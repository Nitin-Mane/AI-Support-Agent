"""Add response schemas required when Gateway imports the REST API definition."""

from provision import session, state

api = session.client("apigateway")
for resource in api.get_resources(restApiId=state["api_id"])["items"]:
    if "GET" not in resource.get("resourceMethods", {}):
        continue
    parameter = "order_id" if "order_id" in resource["path"] else "customer_id"
    api.update_method(
        restApiId=state["api_id"],
        resourceId=resource["id"],
        httpMethod="GET",
        patchOperations=[
            {
                "op": "add",
                "path": "/requestParameters/method.request.path." + parameter,
                "value": "true",
            }
        ],
    )
    api.put_method_response(
        restApiId=state["api_id"],
        resourceId=resource["id"],
        httpMethod="GET",
        statusCode="200",
        responseModels={"application/json": "Empty"},
    )
api.create_deployment(restApiId=state["api_id"], stageName="prod")
control = session.client("bedrock-agentcore-control")
target = control.get_gateway_target(
    gatewayIdentifier=state["gateway_id"], targetId=state["order_target"]
)
response = control.update_gateway_target(
    gatewayIdentifier=state["gateway_id"],
    targetId=state["order_target"],
    name=target["name"],
    targetConfiguration=target["targetConfiguration"],
    credentialProviderConfigurations=[{"credentialProviderType": "GATEWAY_IAM_ROLE"}],
)
print("Order target:", response["status"])
