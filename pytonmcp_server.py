import os
import sys
import json
import time
import asyncio
import configparser
import boto3
import webbrowser
from py_mini_racer import py_mini_racer
from pydantic import BaseModel, ValidationError
from typing import Optional

# Set environment variable
os.environ["AWS_SDK_JS_SUPPRESS_MAINTENANCE_MODE_MESSAGE"] = "1"

# Dummy schema definitions to mimic the TypeScript schemas
ListToolsRequestSchema = "ListToolsRequestSchema"
CallToolRequestSchema = "CallToolRequestSchema"

# Import equivalents for "ts-morph" functionality are not available in Python.
# We will simulate the behavior of wrapUserCode using a simple text manipulation.
def wrapUserCode(userCode: str) -> str:
    lines = userCode.splitlines()
    if not lines:
        return userCode
    # Find the index of the last non-empty line
    last_index = len(lines) - 1
    while last_index >= 0 and lines[last_index].strip() == "":
        last_index -= 1
    if last_index >= 0:
        last_line = lines[last_index].strip()
        # In the original code, if the last statement is an ExpressionStatement,
        # it is replaced with a return statement of that expression.
        # We simulate that by unconditionally replacing the last non-empty line with a return statement.
        lines[last_index] = "return " + last_line
    return "\n".join(lines)

# Create JavaScript virtual machine context functions
def createContext(obj: dict) -> dict:
    return obj

async def runInContext(js_code: str, context: dict):
    # Using py_mini_racer to evaluate JavaScript code; note that context injection is not fully supported.
    ctx = py_mini_racer.MiniRacer()
    # In the original code, AWS is provided in the context.
    # We simulate this by setting a global variable in the JS context if possible.
    # However, py_mini_racer does not allow direct injection of complex Python objects.
    # Thus, we assume that the user's code does not actually invoke AWS functionality in this simulation.
    try:
        result = ctx.eval(js_code)
    except Exception as e:
        raise Exception(f"Error executing JavaScript code: {e}")
    return result

# Minimal implementations of the Server and StdioServerTransport classes
class Server:
    def __init__(self, config: dict, capabilities: dict):
        self.config = config
        self.capabilities = capabilities
        self.handlers = {}
    def setRequestHandler(self, schema, handler):
        self.handlers[schema] = handler
    async def connect(self, transport):
        await transport.connect()
        return

class StdioServerTransport:
    async def connect(self):
        sys.stderr.write("Local Machine MCP Server running on stdio\n")
        return

# Global variables for selected profile and credentials
selectedProfile: Optional[str] = None
selectedProfileCredentials = None
selectedProfileRegion: str = "us-east-1"

# Pydantic models to simulate Zod schemas
class RunAwsCodeSchema(BaseModel):
    reasoning: str
    code: str
    profileName: Optional[str] = None
    region: Optional[str] = None

class SelectProfileSchema(BaseModel):
    profile: str
    region: Optional[str] = None

# Create text response function
def createTextResponse(text: str) -> dict:
    return {
        "content": [
            {
                "type": "text",
                "text": text
            }
        ]
    }

# Function to list AWS credentials and configs
async def listCredentials():
    credentials = {}
    configs = {}
    error = None
    try:
        cp = configparser.ConfigParser()
        cp.read(os.path.expanduser("~/.aws/credentials"))
        credentials = {section: dict(cp.items(section)) for section in cp.sections()}
    except Exception as err:
        error = f"Failed to load credentials: {err}"
    try:
        cp2 = configparser.ConfigParser()
        cp2.read(os.path.expanduser("~/.aws/config"))
        configs = {section: dict(cp2.items(section)) for section in cp2.sections()}
    except Exception as err:
        error = f"Failed to load configs: {err}"
    profiles = {}
    profiles.update(credentials or {})
    profiles.update(configs or {})
    return {"profiles": profiles, "error": error}

# Function to get AWS credentials based on the provided profile details
async def getCredentials(creds: dict, profileName: str):
    if "sso_start_url" in creds:
        region = creds.get("region", "us-east-1")
        ssoStartUrl = creds["sso_start_url"]
        oidc = boto3.client("sso-oidc", region_name=region)
        registration = oidc.register_client(clientName="chatwithcloud", clientType="public")
        auth = oidc.start_device_authorization(
            clientId=registration["clientId"],
            clientSecret=registration["clientSecret"],
            startUrl=ssoStartUrl
        )
        # open this in URL browser
        if auth.get("verificationUriComplete"):
            webbrowser.open(auth["verificationUriComplete"])
        # Polling for token every 2.5 seconds
        while True:
            try:
                createTokenResponse = oidc.create_token(
                    clientId=registration["clientId"],
                    clientSecret=registration["clientSecret"],
                    grantType="urn:ietf:params:oauth:grant-type:device_code",
                    deviceCode=auth["deviceCode"]
                )
                sso = boto3.client("sso", region_name=region)
                credentials_response = sso.get_role_credentials(
                    accessToken=createTokenResponse["accessToken"],
                    accountId=creds["sso_account_id"],
                    roleName=creds["sso_role_name"]
                )
                return credentials_response["roleCredentials"]
            except Exception as error_obj:
                # In the original code, errors are caught and suppressed until a valid token is returned
                if str(error_obj) is not None:
                    pass
            await asyncio.sleep(2.5)
    else:
        return useAWSCredentialsProvider(profileName)

# Function to use AWS credentials provider
def useAWSCredentialsProvider(profileName: str, region: str = "us-east-1", roleArn: Optional[str] = None):
    # Using boto3's Session to simulate fromNodeProviderChain functionality
    session = boto3.Session(profile_name=profileName, region_name=region)
    credentials = session.get_credentials().get_frozen_credentials()
    # Return credentials as a dictionary
    return {
        "access_key": credentials.access_key,
        "secret_key": credentials.secret_key,
        "token": credentials.token
    }

# Create the server instance with configuration and capabilities
server = Server(
    {
        "name": "aws-mcp",
        "version": "1.0.0"
    },
    {
        "capabilities": {
            "tools": {}
        }
    }
)

# Set request handler for listing tools
async def list_tools_handler(request=None, c=None):
    return {
        "tools": [
            {
                "name": "run-aws-code",
                "description": "Run AWS code",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "reasoning": {
                            "type": "string",
                            "description": "The reasoning behind the code"
                        },
                        "code": {
                            "type": "string",
                            "description": codePrompt
                        },
                        "profileName": {
                            "type": "string",
                            "description": "Name of the AWS profile to use"
                        },
                        "region": {
                            "type": "string",
                            "description": "Region to use (if not provided, us-east-1 is used)"
                        }
                    },
                    "required": ["reasoning", "code"]
                }
            },
            {
                "name": "list-credentials",
                "description": "List all AWS credentials/configs/profiles that are configured/usable on this machine",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "select-profile",
                "description": "Selects AWS profile to use for subsequent interactions. If needed, does SSO authentication",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "profile": {
                            "type": "string",
                            "description": "Name of the AWS profile to select"
                        },
                        "region": {
                            "type": "string",
                            "description": "Region to use (if not provided, us-east-1 is used)"
                        }
                    },
                    "required": ["profile"]
                }
            }
        ]
    }

# The code prompt string
codePrompt = ("Your job is to answer questions about AWS environment by writing Javascript code using AWS SDK V2. "
" The code must be adhering to a few rules:\n"
"- Must be preferring promises over callbacks\n"
"- Think step-by-step before writing the code, approach it logically\n"
"- MUST written in Javascript (NodeJS) using AWS-SDK V2\n"
"- Avoid hardcoded values like ARNs\n"
"- Code written should be as parallel as possible enabling the fastest and the most optimal execution\n"
"- Code should be handling errors gracefully, especially when doing multiple SDK calls (e.g. when mapping over an array). Each error should be handled and logged with a reason, script should continue to run despite errors\n"
"- DO NOT require or import \"aws-sdk\", it is already available as \"AWS\" variable\n"
"- Access to 3rd party libraries apart from \"aws-sdk\" is not allowed or possible\n"
"- Data returned from AWS-SDK must be returned as JSON containing only the minimal amount of data that is needed to answer the question. All extra data must be filtered out\n"
"- Code MUST \"return\" a value: string, number, boolean or JSON object. If code does not return anything, it will be considered as FAILED\n"
"- Whenever tool/function call fails, retry it 3 times before giving up with an improved version of the code based on the returned feedback\n"
"- When listing resources, ensure pagination is handled correctly so that all resources are returned\n"
"- Do not include any comments in the code\n"
"- When doing reduce, don't forget to provide an initial value\n"
"- Try to write code that returns as few data as possible to answer without any additional processing required after the code is run\n"
"- This tool can ONLY write code that interacts with AWS. It CANNOT generate charts, tables, graphs, etc. Please use artifacts for that instead\n"
"Be concise, professional and to the point. Do not give generic advice, always reply with detailed & contextual data sourced from the current AWS environment. Assume user always wants to proceed, do not ask for confirmation. I'll tip you $200 if you do this right.")

server.setRequestHandler(ListToolsRequestSchema, list_tools_handler)

# Handle tool execution request
async def call_tool_handler(request, c):
    global selectedProfile, selectedProfileCredentials, selectedProfileRegion
    params = request.get("params", {})
    name = params.get("name")
    args = params.get("arguments", {})
    try:
        credentials_data = await listCredentials()
        profiles = credentials_data.get("profiles", {})
        error_msg = credentials_data.get("error")
        if name == "run-aws-code":
            try:
                parsed = RunAwsCodeSchema.parse_obj(args)
            except ValidationError as ve:
                raise Exception(f"Invalid arguments: {', '.join([f'{'.'.join(err['loc'])}: {err['msg']}' for err in ve.errors()])}")
            reasoning = parsed.reasoning
            code = parsed.code
            profileName = parsed.profileName
            region = parsed.region
            if not selectedProfile and not profileName:
                available_profiles = ", ".join(list(profiles.keys()))
                return createTextResponse(f"Please select a profile first using the 'select-profile' tool! Available profiles: {available_profiles}")
            if profileName:
                selectedProfileCredentials = await getCredentials(profiles.get(profileName, {}), profileName)
                selectedProfile = profileName
                selectedProfileRegion = region if region is not None else "us-east-1"
            # Update AWS configuration (simulation)
            AWS_config = {
                "region": selectedProfileRegion,
                "credentials": selectedProfileCredentials
            }
            wrappedCode = wrapUserCode(code)
            wrappedIIFECode = f"(async function() {{ return (async () => {{ {wrappedCode} }})(); }})()"
            result = await runInContext(wrappedIIFECode, createContext({"AWS": AWS_config}))
            return createTextResponse(json.dumps(result))
        elif name == "list-credentials":
            return createTextResponse(json.dumps({"profiles": list(profiles.keys()), "error": error_msg}))
        elif name == "select-profile":
            try:
                parsed = SelectProfileSchema.parse_obj(args)
            except ValidationError as ve:
                raise Exception(f"Invalid arguments: {', '.join([f'{'.'.join(err['loc'])}: {err['msg']}' for err in ve.errors()])}")
            profile = parsed.profile
            region = parsed.region
            credentials = await getCredentials(profiles.get(profile, {}), profile)
            selectedProfile = profile
            selectedProfileCredentials = credentials
            selectedProfileRegion = region if region is not None else "us-east-1"
            return createTextResponse("Authenticated!")
        else:
            raise Exception(f"Unknown tool: {name}")
    except ValidationError as ve:
        raise Exception(f"Invalid arguments: {', '.join([f'{'.'.join(err['loc'])}: {err['msg']}' for err in ve.errors()])}")
    except Exception as error_obj:
        raise error_obj

server.setRequestHandler(CallToolRequestSchema, call_tool_handler)

# Start the server
async def main():
    transport = StdioServerTransport()
    await server.connect(transport)
    
# If run as the main module, start the server event loop.
if __name__ == "__main__":
    asyncio.run(main())
    
