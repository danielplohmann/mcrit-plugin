#!/usr/bin/env python3
"""
Comprehensive HCLI Plugin Validation Script
Validates ida-plugin.json and plugin structure according to HCLI standards
"""

import json
import os
import sys
from pathlib import Path

def print_header(text):
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70)

def print_success(text):
    print(f"✓ {text}")

def print_error(text):
    print(f"✗ {text}")

def print_warning(text):
    print(f"⚠ {text}")

class PluginValidator:
    def __init__(self, plugin_dir):
        self.plugin_dir = Path(plugin_dir)
        self.errors = []
        self.warnings = []
        self.plugin_json_path = self.plugin_dir / "ida-plugin.json"
        self.plugin_data = None

    def validate_all(self):
        """Run all validations"""
        print_header("HCLI Plugin Validation")
        print(f"Plugin Directory: {self.plugin_dir}\n")

        # Step 1: JSON syntax
        if not self.validate_json_syntax():
            return False

        # Step 2: Required fields
        if not self.validate_required_fields():
            return False

        # Step 3: Field formats
        self.validate_field_formats()

        # Step 4: File references
        self.validate_file_references()

        # Step 5: Settings schema
        self.validate_settings_schema()

        # Step 6: Python dependencies
        self.validate_python_dependencies()

        # Step 7: Directory structure
        self.validate_directory_structure()

        # Print summary
        self.print_summary()

        return len(self.errors) == 0

    def validate_json_syntax(self):
        """Validate JSON syntax"""
        print_header("JSON Syntax Validation")

        if not self.plugin_json_path.exists():
            print_error(f"ida-plugin.json not found at {self.plugin_json_path}")
            return False

        try:
            with open(self.plugin_json_path) as f:
                self.plugin_data = json.load(f)
            print_success("JSON syntax is valid")
            print_success(f"Loaded from: {self.plugin_json_path}")
            return True
        except json.JSONDecodeError as e:
            print_error(f"Invalid JSON: {e}")
            return False

    def validate_required_fields(self):
        """Validate all required fields are present"""
        print_header("Required Fields Validation")

        # Check IDAMetadataDescriptorVersion
        if 'IDAMetadataDescriptorVersion' not in self.plugin_data:
            self.errors.append('Missing IDAMetadataDescriptorVersion')
            print_error('Missing IDAMetadataDescriptorVersion')
            return False

        if self.plugin_data['IDAMetadataDescriptorVersion'] != 1:
            self.errors.append('IDAMetadataDescriptorVersion must be 1')
            print_error(f'IDAMetadataDescriptorVersion must be 1, got: {self.plugin_data["IDAMetadataDescriptorVersion"]}')
            return False

        print_success(f'IDAMetadataDescriptorVersion: {self.plugin_data["IDAMetadataDescriptorVersion"]}')

        # Check plugin object
        if 'plugin' not in self.plugin_data:
            self.errors.append('Missing plugin object')
            print_error('Missing plugin object')
            return False

        plugin = self.plugin_data['plugin']

        # Required fields
        required = {
            'name': str,
            'version': str,
            'entryPoint': str,
        }

        all_required_present = True
        for field, expected_type in required.items():
            if field not in plugin:
                self.errors.append(f'Missing required field: plugin.{field}')
                print_error(f'Missing required field: plugin.{field}')
                all_required_present = False
            elif not isinstance(plugin[field], expected_type):
                self.errors.append(f'Field plugin.{field} should be {expected_type.__name__}')
                print_error(f'Field plugin.{field} should be {expected_type.__name__}')
                all_required_present = False
            else:
                print_success(f'plugin.{field}: {plugin[field]}')

        return all_required_present

    def validate_field_formats(self):
        """Validate field formats"""
        print_header("Field Format Validation")

        plugin = self.plugin_data['plugin']

        # Validate version format (x.y.z)
        if 'version' in plugin:
            version = plugin['version']
            parts = version.split('.')
            if len(parts) != 3 or not all(p.isdigit() for p in parts):
                self.errors.append(f'Version must be in x.y.z format, got: {version}')
                print_error(f'Version must be in x.y.z format, got: {version}')
            else:
                print_success(f'Version format valid: {version}')

        # Check idaVersions format (should be string, not array)
        if 'idaVersions' in plugin:
            ida_versions = plugin['idaVersions']
            if isinstance(ida_versions, list):
                self.errors.append('idaVersions should be a string with semantic versioning (e.g., ">=9.0"), not an array')
                print_error('idaVersions should be a string, not an array')
            elif isinstance(ida_versions, str):
                print_success(f'idaVersions: {ida_versions}')
            else:
                self.errors.append('idaVersions has invalid type')
                print_error(f'idaVersions has invalid type: {type(ida_versions)}')

        # Check optional recommended fields
        optional_recommended = {
            'description': str,
            'license': str,
            'urls': dict,
            'authors': list,
            'categories': list,
            'keywords': list,
        }

        for field, expected_type in optional_recommended.items():
            if field in plugin:
                if isinstance(plugin[field], expected_type):
                    if field == 'authors' and len(plugin[field]) > 0:
                        author = plugin[field][0]
                        if 'name' in author and 'email' in author:
                            print_success(f'Author: {author["name"]} <{author["email"]}>')
                        else:
                            print_success(f'{field}: present ({len(plugin[field])} items)')
                    elif field == 'categories':
                        print_success(f'Categories: {", ".join(plugin[field])}')
                    elif field == 'keywords':
                        print_success(f'Keywords: {len(plugin[field])} keywords')
                    elif field == 'urls' and 'repository' in plugin[field]:
                        print_success(f'Repository URL: {plugin[field]["repository"]}')
                    else:
                        print_success(f'{field}: present')
                else:
                    self.warnings.append(f'{field} has unexpected type')
                    print_warning(f'{field} has unexpected type: expected {expected_type.__name__}, got {type(plugin[field]).__name__}')
            else:
                if field in ['urls', 'authors']:  # These are actually required for HCLI
                    self.warnings.append(f'Recommended field missing: plugin.{field}')
                    print_warning(f'Recommended field missing: plugin.{field}')

    def validate_file_references(self):
        """Validate all referenced files exist"""
        print_header("File References Validation")

        plugin = self.plugin_data['plugin']

        # Check entryPoint exists
        if 'entryPoint' in plugin:
            entry_point = self.plugin_dir / plugin['entryPoint']
            if entry_point.exists():
                print_success(f'Entry point exists: {plugin["entryPoint"]}')
            else:
                self.errors.append(f'Entry point file not found: {plugin["entryPoint"]}')
                print_error(f'Entry point file not found: {entry_point}')

        # Check logo path
        if 'logoPath' in plugin:
            logo_path = self.plugin_dir / plugin['logoPath']
            if logo_path.exists():
                print_success(f'Logo file exists: {plugin["logoPath"]}')
            else:
                self.warnings.append(f'Logo file not found: {plugin["logoPath"]}')
                print_warning(f'Logo file not found: {logo_path}')

    def validate_settings_schema(self):
        """Validate settings schema"""
        print_header("Settings Schema Validation")

        plugin = self.plugin_data['plugin']

        if 'settings' not in plugin:
            print("No settings defined (optional)")
            return

        settings = plugin['settings']

        if not isinstance(settings, list):
            self.errors.append('settings must be a list')
            print_error('settings must be a list')
            return

        print_success(f'Settings array with {len(settings)} items')

        # Validate each setting
        valid_types = ['string', 'boolean', 'number', 'integer']

        for i, setting in enumerate(settings):
            required_fields = ['key', 'type', 'name']
            missing = [f for f in required_fields if f not in setting]

            if missing:
                self.errors.append(f'Setting #{i} missing fields: {", ".join(missing)}')
                print_error(f'Setting #{i} missing fields: {", ".join(missing)}')
                continue

            # Validate type
            if setting['type'] not in valid_types:
                self.warnings.append(f'Setting "{setting["key"]}" has unusual type: {setting["type"]}')
                print_warning(f'Setting "{setting["key"]}" has unusual type: {setting["type"]}')

            # Check type/default consistency
            if 'default' in setting:
                default_val = setting['default']
                declared_type = setting['type']

                if declared_type == 'boolean' and not isinstance(default_val, bool):
                    self.warnings.append(f'Setting "{setting["key"]}": type is boolean but default is {type(default_val).__name__}')
                    print_warning(f'Setting "{setting["key"]}": type is boolean but default is {type(default_val).__name__}')
                elif declared_type in ['number', 'integer'] and not isinstance(default_val, (int, float)):
                    self.warnings.append(f'Setting "{setting["key"]}": type is {declared_type} but default is {type(default_val).__name__}')
                    print_warning(f'Setting "{setting["key"]}": type is {declared_type} but default is {type(default_val).__name__}')
                elif declared_type == 'string' and not isinstance(default_val, str):
                    self.warnings.append(f'Setting "{setting["key"]}": type is string but default is {type(default_val).__name__}')
                    print_warning(f'Setting "{setting["key"]}": type is string but default is {type(default_val).__name__}')

        print_success(f'All {len(settings)} settings have required fields')

    def validate_python_dependencies(self):
        """Validate Python dependencies format"""
        print_header("Python Dependencies Validation")

        plugin = self.plugin_data['plugin']

        if 'pythonDependencies' not in plugin:
            print("No Python dependencies defined (optional)")
            return

        deps = plugin['pythonDependencies']

        if not isinstance(deps, list):
            self.errors.append('pythonDependencies must be a list')
            print_error('pythonDependencies must be a list')
            return

        print_success(f'Python dependencies: {len(deps)} packages')

        for dep in deps:
            if not isinstance(dep, str):
                self.errors.append(f'Dependency must be string, got: {type(dep).__name__}')
                print_error(f'Dependency must be string, got: {dep}')
            else:
                print(f'  - {dep}')

    def validate_directory_structure(self):
        """Validate plugin directory structure"""
        print_header("Directory Structure Validation")

        print(f"Plugin directory: {self.plugin_dir}")
        print(f"\nFiles in plugin directory:")

        files = sorted(self.plugin_dir.rglob('*'))
        for f in files:
            if f.is_file():
                rel_path = f.relative_to(self.plugin_dir)
                print(f"  {rel_path}")

        print_success("Directory structure validated")

    def print_summary(self):
        """Print validation summary"""
        print_header("Validation Summary")

        if len(self.errors) == 0 and len(self.warnings) == 0:
            print("\n🎉 ALL VALIDATIONS PASSED! 🎉")
            print("\nYour plugin is HCLI-compliant and ready for publication!")
            print("\nNext steps:")
            print("  1. Create a GitHub release (tag v{})".format(self.plugin_data['plugin']['version']))
            print("  2. Wait ~24 hours for HCLI indexer")
            print("  3. Plugin will appear on plugins.hex-rays.com")
            print("  4. Users can install via: hcli plugin install {}".format(self.plugin_data['plugin']['name']))
            return True

        if self.errors:
            print(f"\n❌ VALIDATION FAILED: {len(self.errors)} error(s)")
            print("\nErrors:")
            for error in self.errors:
                print(f"  ✗ {error}")

        if self.warnings:
            print(f"\n⚠️  {len(self.warnings)} warning(s):")
            for warning in self.warnings:
                print(f"  ⚠ {warning}")

        if len(self.errors) > 0:
            print("\n❌ Plugin is NOT ready for publication. Please fix errors above.")
            return False
        else:
            print("\n✅ Plugin passes validation with warnings.")
            print("   Warnings should be addressed but won't prevent publication.")
            return True

def main():
    # Determine plugin directory
    script_dir = Path(__file__).parent
    plugin_dir = script_dir / "mcrit-plugins" / "ida"

    if not plugin_dir.exists():
        print(f"Error: Plugin directory not found: {plugin_dir}")
        sys.exit(1)

    validator = PluginValidator(plugin_dir)
    success = validator.validate_all()

    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
