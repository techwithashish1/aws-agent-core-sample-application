"""AWS Bedrock client wrapper for LLM interactions."""

from typing import Dict, Any, Optional, List
import boto3
import json
from botocore.exceptions import ClientError
import structlog

from config import settings

logger = structlog.get_logger()


class BedrockClient:
    """Client for interacting with AWS Bedrock LLM."""

    def __init__(
        self,
        model_id: Optional[str] = None,
        region: Optional[str] = None
    ):
        """Initialize Bedrock client.
        
        Args:
            model_id: Bedrock model ID (defaults to settings)
            region: AWS region (defaults to settings)
        """
        self.model_id = model_id or settings.bedrock_model_id
        self.region = region or settings.bedrock_region
        self.client = boto3.client('bedrock-runtime', region_name=self.region)
        self.logger = logger.bind(component="bedrock_client")

    def invoke_model(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """Invoke the Bedrock model with a prompt.
        
        Args:
            prompt: User prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            system_prompt: System prompt for context
            
        Returns:
            Model response
        """
        try:
            max_tokens = max_tokens or settings.max_tokens
            temperature = temperature or settings.temperature

            # Prepare request based on model type
            if "anthropic.claude" in self.model_id:
                request_body = self._prepare_claude_request(
                    prompt, max_tokens, temperature, system_prompt
                )
            elif "amazon.titan" in self.model_id:
                request_body = self._prepare_titan_request(
                    prompt, max_tokens, temperature
                )
            else:
                raise ValueError(f"Unsupported model: {self.model_id}")

            self.logger.info(
                "invoking_bedrock_model",
                model_id=self.model_id,
                prompt_length=len(prompt)
            )

            response = self.client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body)
            )

            response_body = json.loads(response['body'].read())
            
            return self._parse_response(response_body)

        except ClientError as e:
            self.logger.error("bedrock_invocation_failed", error=str(e))
            raise
        except Exception as e:
            self.logger.error("unexpected_error", error=str(e))
            raise

    def _prepare_claude_request(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
        system_prompt: Optional[str]
    ) -> Dict[str, Any]:
        """Prepare request body for Claude models.
        
        Args:
            prompt: User prompt
            max_tokens: Maximum tokens
            temperature: Sampling temperature
            system_prompt: System prompt
            
        Returns:
            Request body
        """
        messages = [{"role": "user", "content": prompt}]
        
        request = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages
        }
        
        if system_prompt:
            request["system"] = system_prompt
            
        return request

    def _prepare_titan_request(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float
    ) -> Dict[str, Any]:
        """Prepare request body for Titan models.
        
        Args:
            prompt: User prompt
            max_tokens: Maximum tokens
            temperature: Sampling temperature
            
        Returns:
            Request body
        """
        return {
            "inputText": prompt,
            "textGenerationConfig": {
                "maxTokenCount": max_tokens,
                "temperature": temperature,
                "topP": 0.9
            }
        }

    def _parse_response(self, response_body: Dict[str, Any]) -> Dict[str, Any]:
        """Parse model response.
        
        Args:
            response_body: Raw response body
            
        Returns:
            Parsed response
        """
        if "anthropic.claude" in self.model_id:
            content = response_body.get("content", [])
            if content and len(content) > 0:
                text = content[0].get("text", "")
            else:
                text = ""
            
            return {
                "text": text,
                "stop_reason": response_body.get("stop_reason"),
                "usage": response_body.get("usage", {})
            }
        
        elif "amazon.titan" in self.model_id:
            results = response_body.get("results", [])
            if results:
                text = results[0].get("outputText", "")
            else:
                text = ""
            
            return {
                "text": text,
                "stop_reason": response_body.get("completionReason"),
                "usage": {
                    "input_tokens": response_body.get("inputTextTokenCount"),
                    "output_tokens": response_body.get("results", [{}])[0].get("tokenCount")
                }
            }
        
        return {"text": "", "error": "Unknown model type"}

    async def ainvoke_model(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """Async version of invoke_model.
        
        Args:
            prompt: User prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            system_prompt: System prompt for context
            
        Returns:
            Model response
        """
        # For now, just call the sync version
        # In production, use aioboto3 for true async
        return self.invoke_model(prompt, max_tokens, temperature, system_prompt)
