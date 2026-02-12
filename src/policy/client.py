"""AgentCore Policy Client for AWS Resource Manager.

This module provides policy management capabilities using Amazon Bedrock AgentCore Policy.
"""

import logging
from typing import Optional, List, Dict, Any

from bedrock_agentcore_starter_toolkit.operations.policy.client import PolicyClient
from bedrock_agentcore_starter_toolkit.operations.gateway.client import GatewayClient
from botocore.exceptions import ClientError

from config import settings

logger = logging.getLogger("agentcore-policy")


class PolicyManager:
    """Manager for AgentCore Policy operations.
    
    Provides methods to create policy engines, policies, and attach
    them to gateways for enforcing access control on agent tools.
    """

    def __init__(self, region_name: Optional[str] = None):
        """Initialize the Policy Manager.
        
        Args:
            region_name: AWS region for the policy client. Defaults to settings.aws_region.
        """
        self.region = region_name or settings.aws_region
        self.policy_client = PolicyClient(region_name=self.region)
        self.gateway_client = GatewayClient(region_name=self.region)
        self.policy_engine_id: Optional[str] = None
        self.policy_engine_arn: Optional[str] = None
        
        logger.info(f"PolicyManager initialized for region: {self.region}")

    def create_policy_engine(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new Policy Engine or get existing one.
        
        Args:
            name: Unique name for the policy engine. Defaults to agent_name_policy_engine.
            description: Human-readable description.
            
        Returns:
            Dict containing policy engine details including 'policyEngineId' and 'policyEngineArn'.
        """
        engine_name = name or f"{settings.agent_name.replace('-', '_')}_policy_engine"
        engine_description = description or f"Policy engine for {settings.agent_description}"
        
        try:
            logger.info(f"Creating policy engine: {engine_name}")
            
            engine = self.policy_client.create_or_get_policy_engine(
                name=engine_name,
                description=engine_description
            )
            
            self.policy_engine_id = engine['policyEngineId']
            self.policy_engine_arn = engine['policyEngineArn']
            
            logger.info(f"Policy engine ready: {self.policy_engine_id}")
            return engine
            
        except ClientError as e:
            logger.error(f"Failed to create policy engine: {e}")
            raise

    def attach_to_gateway(
        self,
        gateway_id: str,
        mode: str = "ENFORCE"
    ) -> None:
        """Attach policy engine to a gateway.
        
        Args:
            gateway_id: ID of the gateway to attach to.
            mode: Policy enforcement mode - "ENFORCE" or "LOG_ONLY".
                  - ENFORCE: Actively blocks non-compliant requests.
                  - LOG_ONLY: Evaluates but doesn't block (for testing).
        """
        if not self.policy_engine_arn:
            raise ValueError("Policy engine not created. Call create_policy_engine() first.")
        
        try:
            logger.info(f"Attaching policy engine to gateway {gateway_id} in {mode} mode")
            
            self.gateway_client.update_gateway_policy_engine(
                gateway_identifier=gateway_id,
                policy_engine_arn=self.policy_engine_arn,
                mode=mode
            )
            
            logger.info(f"Policy engine attached to gateway")
            
        except ClientError as e:
            logger.error(f"Failed to attach policy engine: {e}")
            raise

    def detach_from_gateway(self, gateway_id: str) -> None:
        """Detach policy engine from a gateway.
        
        Args:
            gateway_id: ID of the gateway to detach from.
        """
        try:
            logger.info(f"Detaching policy engine from gateway {gateway_id}")
            
            # Pass empty policy engine to detach
            self.gateway_client.update_gateway_policy_engine(
                gateway_identifier=gateway_id,
                policy_engine_arn="",
                mode="ENFORCE"
            )
            
            logger.info("Policy engine detached from gateway")
            
        except ClientError as e:
            logger.error(f"Failed to detach policy engine: {e}")
            raise

    def create_policy(
        self,
        name: str,
        cedar_statement: str,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a Cedar policy in the policy engine.
        
        Args:
            name: Unique name for the policy.
            cedar_statement: Cedar policy statement.
            description: Human-readable description of what the policy does.
            
        Returns:
            Dict containing policy details including 'policyId'.
        """
        if not self.policy_engine_id:
            raise ValueError("Policy engine not created. Call create_policy_engine() first.")
        
        try:
            logger.info(f"Creating policy: {name}")
            
            policy = self.policy_client.create_or_get_policy(
                policy_engine_id=self.policy_engine_id,
                name=name,
                description=description or f"Policy: {name}",
                definition={"cedar": {"statement": cedar_statement}}
            )
            
            logger.info(f"Policy created: {policy['policyId']}")
            return policy
            
        except ClientError as e:
            logger.error(f"Failed to create policy: {e}")
            raise

    def generate_policy_from_nl(
        self,
        natural_language: str,
        gateway_arn: str,
        target_schemas: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """Generate Cedar policies from natural language description.
        
        Uses NL2Cedar to convert plain English policy descriptions to Cedar syntax.
        
        Args:
            natural_language: Policy description in plain English.
            gateway_arn: ARN of the gateway the policies will apply to.
            target_schemas: Optional list of target schemas for context.
            
        Returns:
            List of generated policy definitions.
        """
        try:
            logger.info(f"Generating policy from: {natural_language[:100]}...")
            
            result = self.policy_client.generate_policy(
                gateway_arn=gateway_arn,
                natural_language=natural_language,
                target_schemas=target_schemas or []
            )
            
            generated = result.get('generatedPolicies', [])
            logger.info(f"Generated {len(generated)} policies")
            return generated
            
        except ClientError as e:
            logger.error(f"Failed to generate policy: {e}")
            raise

    def list_policies(self) -> List[Dict[str, Any]]:
        """List all policies in the current policy engine.
        
        Returns:
            List of policy summaries.
        """
        if not self.policy_engine_id:
            return []
        
        try:
            response = self.policy_client.list_policies(
                policy_engine_id=self.policy_engine_id
            )
            # Handle different response formats
            if isinstance(response, dict):
                return response.get('policies', [])
            return response
            
        except ClientError as e:
            logger.error(f"Failed to list policies: {e}")
            return []

    def delete_policy(self, policy_id: str) -> None:
        """Delete a policy from the policy engine.
        
        Args:
            policy_id: ID of the policy to delete.
        """
        if not self.policy_engine_id:
            raise ValueError("Policy engine not set.")
        
        try:
            logger.info(f"Deleting policy: {policy_id}")
            
            self.policy_client.delete_policy(
                policy_engine_id=self.policy_engine_id,
                policy_id=policy_id
            )
            
            logger.info("Policy deleted")
            
        except ClientError as e:
            logger.error(f"Failed to delete policy: {e}")
            raise

    def cleanup(self) -> None:
        """Clean up all policies and the policy engine.
        
        This will:
        1. Delete all policies in the engine
        2. Delete the policy engine itself
        """
        if not self.policy_engine_id:
            logger.warning("No policy engine to clean up")
            return
        
        try:
            logger.info(f"Cleaning up policy engine: {self.policy_engine_id}")
            
            self.policy_client.cleanup_policy_engine(self.policy_engine_id)
            
            self.policy_engine_id = None
            self.policy_engine_arn = None
            
            logger.info("Policy engine cleaned up")
            
        except ClientError as e:
            logger.error(f"Failed to cleanup policy engine: {e}")
            raise

    def list_policy_engines(self) -> List[Dict[str, Any]]:
        """List all policy engines in the account.
        
        Returns:
            List of policy engine summaries.
        """
        try:
            engines = self.policy_client.list_policy_engines()
            return engines
        except ClientError as e:
            logger.error(f"Failed to list policy engines: {e}")
            return []
