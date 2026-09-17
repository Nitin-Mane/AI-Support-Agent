"""Create the Titan V2 catalog index in an existing OpenSearch collection.

Uses the normal AWS credential chain and signs the exact request body, including
the payload-hash header required by OpenSearch Serverless. No resources other
than the named index are provisioned by this command.
"""
import argparse
import hashlib
import json
import re

import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.httpsession import URLLib3Session


def create_index(endpoint, region, index_name):
    if not re.fullmatch(r'https://[a-z0-9]+\.' + re.escape(region) + r'\.aoss\.amazonaws\.com', endpoint):
        raise ValueError('Endpoint must be the AWS OpenSearch Serverless collection endpoint in the selected region')
    if not re.fullmatch(r'[a-z][a-z0-9_-]{0,127}', index_name):
        raise ValueError('Use a lowercase index name beginning with a letter')
    body = json.dumps({
        'settings': {'index.knn': True},
        'mappings': {'properties': {
            'vector': {'type': 'knn_vector', 'dimension': 1024,
                       'method': {'name': 'hnsw', 'engine': 'faiss', 'space_type': 'l2'}},
            'text': {'type': 'text'},
            'metadata': {'type': 'text', 'index': False},
        }},
    }).encode('utf-8')
    session = boto3.Session(region_name=region)
    credentials = session.get_credentials()
    if credentials is None:
        raise RuntimeError('AWS credentials are not configured')
    request = AWSRequest(method='PUT', url=endpoint+'/'+index_name, data=body,
                         headers={'Content-Type': 'application/json',
                                  'X-Amz-Content-Sha256': hashlib.sha256(body).hexdigest()})
    SigV4Auth(credentials.get_frozen_credentials(), 'aoss', region).add_auth(request)
    response = URLLib3Session(timeout=30).send(request.prepare())
    text = response.content.decode('utf-8')
    if response.status_code == 200:
        return {'status': 'created', 'http_status': response.status_code,
                'response': json.loads(text)}
    if response.status_code == 400 and 'resource_already_exists_exception' in text:
        return {'status': 'already_exists', 'http_status': response.status_code,
                'response': json.loads(text)}
    raise RuntimeError(f'Index creation failed: HTTP {response.status_code}: {text}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--endpoint', required=True)
    parser.add_argument('--region', default='us-east-1')
    parser.add_argument('--index', default='catalog')
    args = parser.parse_args()
    print(json.dumps(create_index(args.endpoint.rstrip('/'), args.region, args.index), indent=2))
