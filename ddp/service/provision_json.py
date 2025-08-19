#!/usr/bin/env python3
"""
JSON validation and parsing classes for WiSUN provisioning parameters.

This module provides classes to validate and parse JSON input for the provision API,
based on the parameters used in the provision.py script.
"""

import json
import base64
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, field
from common_executor import ProvisionMode
import wisun.common


class ProvisionValidationError(Exception):
    """Custom exception for provision parameter validation errors"""
    pass


@dataclass
class ProvisionRequest:
    """
    Data class representing a provision request with validation.
    
    Based on the parameters from provision.py script:
    - soc: SoC type (required)
    - jlink_ser: J-Link serial number (optional, but either this or jlink_host required)
    - jlink_host: J-Link IP address/hostname (optional, but either this or jlink_ser required)
    - prov_img: Provision binary file path (required)
    - init_img: Initialization data file path (optional)
    - app: Application file path (optional)
    - nvm3: NVM3 flag (optional, default False)
    - certification: Certification mode (optional, default False)
    - cpms: CPMS mode (optional, default False)
    - oid: Product OID for CPMS mode (optional, required if cpms is True)
    - config: OpenSSL config file path (optional, default 'openssl.conf')
    """
    
    # Required fields
    soc: str
    prov_img: str
    mode: ProvisionMode

    # Connection parameters (at least one required)
    jlink_ser: Optional[str] = None
    jlink_host: Optional[str] = None
    
    # Optional fields
    init_img: Optional[str] = None
    app: Optional[str] = None
    nvm3: bool = False
    certification: bool = False
    cpms: bool = False
    oid: Optional[str] = None
    config: str = 'openssl.conf'
    
    def __post_init__(self):
        """Validate the provision request after initialization"""
        self.validate()
    
    def validate(self):
        """Validate all provision request parameters"""
        
        # Validate SOC type
        if not self.soc:
            raise ProvisionValidationError("SOC type is required") 
        
        if not self.mode:
            raise ProvisionValidationError("Provision mode is required")

        if self.soc not in wisun.common.socs:
            supported_socs = list(wisun.common.socs.keys())
            raise ProvisionValidationError(
                f"Unsupported SoC type: {self.soc}. Supported types: {supported_socs}"
            )
        
        # Validate provision data
        if not self.prov_img:
            raise ProvisionValidationError("Provision file path is required")
        
        if not isinstance(self.prov_img, str):
            raise ProvisionValidationError("Provision file path must be a string")
        
        # Validate connection parameters (at least one required)
        if not self.jlink_ser and not self.jlink_host:
            raise ProvisionValidationError(
                "Either jlink_ser or jlink_host must be provided"
            )
        
        # Validate CPMS mode requirements
        if self.cpms and not self.oid:
            raise ProvisionValidationError(
                "OID is required when CPMS mode is enabled"
            )
        
        # Validate optional file path fields
        if self.init_img is not None and not isinstance(self.init_img, str):
            raise ProvisionValidationError("init_img must be a string (file path)")
        
        if self.app is not None and not isinstance(self.app, str):
            raise ProvisionValidationError("app must be a string (file path)")
    
    @classmethod
    def from_json(cls, json_data: Union[str, Dict[str, Any]]) -> 'ProvisionRequest':
        """
        Create ProvisionRequest from JSON data
        
        Args:
            json_data: JSON string or dictionary
            
        Returns:
            ProvisionRequest instance
            
        Raises:
            ProvisionValidationError: If validation fails
            json.JSONDecodeError: If JSON parsing fails
        """
        
        # Parse JSON if string
        if isinstance(json_data, str):
            try:
                data = json.loads(json_data)
            except json.JSONDecodeError as e:
                raise ProvisionValidationError(f"Invalid JSON format: {e}")
        else:
            data = json_data
        
        if not isinstance(data, dict):
            raise ProvisionValidationError("JSON data must be an object")
        
        # Extract and validate required fields
        soc = data.get('soc')
        if not soc:
            raise ProvisionValidationError("Missing required field: soc")

        mode_value = data.get('mode')
        if mode_value is None:
            raise ProvisionValidationError("Missing required field: mode")
        try:
            mode = ProvisionMode(mode_value)
        except ValueError:
            raise ProvisionValidationError(f"Invalid mode value: {mode_value}")

        provision_data = data.get('prov_img')
        if not provision_data:
            raise ProvisionValidationError("Missing required field: prov_img")
        
        # Validate that it's a string (file path)
        if not isinstance(provision_data, str):
            raise ProvisionValidationError("prov_img must be a string (file path)")
        
        # Extract optional fields (now as file paths, not base64 data)
        init_img = data.get('init_img') if data.get('init_img') else None
        app = data.get('app') if data.get('app') else None
        
        # Validate that file paths are strings if provided
        if init_img is not None and not isinstance(init_img, str):
            raise ProvisionValidationError("init_img must be a string (file path)")
        
        if app is not None and not isinstance(app, str):
            raise ProvisionValidationError("app must be a string (file path)")
        
        # Create and return instance
        return cls(
            soc=soc,
            mode=mode,
            prov_img=provision_data,
            jlink_ser=data.get('jlink_ser'),
            jlink_host=data.get('jlink_host'),
            init_img=init_img,
            app=app,
            nvm3=data.get('nvm3', False),
            certification=data.get('certification', False),
            cpms=data.get('cpms', False),
            oid=data.get('oid'),
            config=data.get('config', 'openssl.conf')
        )
    
    @staticmethod
    def _decode_base64_field(value: Any, field_name: str) -> bytes:
        """
        Decode base64 field value to bytes
        
        Args:
            value: Field value (string or bytes)
            field_name: Field name for error messages
            
        Returns:
            Decoded bytes
            
        Raises:
            ProvisionValidationError: If decoding fails
        """
        if isinstance(value, bytes):
            return value
        
        if isinstance(value, str):
            try:
                return base64.b64decode(value)
            except Exception as e:
                raise ProvisionValidationError(
                    f"Invalid base64 encoding for {field_name}: {e}"
                )
        
        raise ProvisionValidationError(
            f"Field {field_name} must be string (base64) or bytes"
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary representation
        
        Returns:
            Dictionary with base64-encoded binary data
        """
        result = {
            'soc': self.soc,
            'prov_img': self.prov_img,
            'nvm3': self.nvm3,
            'certification': self.certification,
            'cpms': self.cpms,
            'config': self.config
        }
        
        # Add optional fields if present
        if self.jlink_ser:
            result['jlink_ser'] = self.jlink_ser
        
        if self.jlink_host:
            result['jlink_host'] = self.jlink_host
        
        if self.init_img:
            result['init_img'] = self.init_img
        
        if self.app:
            result['app'] = self.app
        
        if self.oid:
            result['oid'] = self.oid
        
        return result
    
    def to_json(self) -> str:
        """
        Convert to JSON string
        
        Returns:
            JSON string representation
        """
        return json.dumps(self.to_dict(), indent=2)
    
    def get_soc_config(self) -> Dict[str, Any]:
        """
        Get SOC configuration from wisun.common
        
        Returns:
            SOC configuration dictionary
        """
        return wisun.common.socs[self.soc]


class ProvisionResponse:
    """
    Class representing a provision response
    """
    
    def __init__(self, success: bool, message: str, 
                 csr_key: Optional[str] = None, 
                 device_serial: Optional[str] = None,
                 error: Optional[str] = None):
        self.success = success
        self.message = message
        self.csr_key = csr_key
        self.device_serial = device_serial
        self.error = error
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = {
            'success': self.success,
            'message': self.message
        }
        
        if self.success:
            result['status'] = 'success'
            if self.csr_key:
                result['csr_key'] = self.csr_key
            if self.device_serial:
                result['device_serial'] = self.device_serial
        else:
            if self.error:
                result['error'] = self.error
        
        return result
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def success_response(cls, message: str, csr_key: Optional[str] = None, 
                        device_serial: Optional[str] = None) -> 'ProvisionResponse':
        """Create a success response"""
        return cls(True, message, csr_key, device_serial)
    
    @classmethod
    def error_response(cls, error: str) -> 'ProvisionResponse':
        """Create an error response"""
        return cls(False, error, error=error)


# Utility functions for JSON validation
def validate_provision_json(json_data: Union[str, Dict[str, Any]]) -> ProvisionRequest:
    """
    Validate provision JSON data and return ProvisionRequest
    
    Args:
        json_data: JSON string or dictionary
        
    Returns:
        ProvisionRequest instance
        
    Raises:
        ProvisionValidationError: If validation fails
    """
    return ProvisionRequest.from_json(json_data)


def get_supported_socs() -> list:
    """Get list of supported SOC types"""
    return list(wisun.common.socs.keys())


# Example usage and testing
if __name__ == '__main__':
    # Example JSON data
    example_json = {
        "soc": "xg25",
        "jlink_ser": "123456789",
        "prov_img": "/path/to/provision_file.bin",
        "mode": 1,
        "nvm3": True,
        "certification": False
    }
    
    try:
        # Test validation
        provision_req = ProvisionRequest.from_json(example_json)
        print("Validation successful!")
        print(f"SOC: {provision_req.soc}")
        print(f"Provision file: {provision_req.prov_img}")
        print(f"SOC config: {provision_req.get_soc_config()}")
        
        # Test JSON conversion
        json_str = provision_req.to_json()
        print(f"JSON representation:\n{json_str}")
        
    except ProvisionValidationError as e:
        print(f"Validation error: {e}")
