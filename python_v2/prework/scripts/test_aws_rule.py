import python_generic_rule as pgr

def test_unrestricted_admin_access():
    """Test detection of unrestricted admin service access through CIDR blocks."""
    test_code = '''
admin_config = {
    "ingress_rules": [{
        "from_port": 22,
        "to_port": 22,
        "protocol": "tcp",
        "cidr_blocks": ["0.0.0.0/0"]
    }]
}
'''
    issues = pgr.check_file_for_rule(
        "python_docs/administration_services_access_should_be_restricted_to_specific_ip_addresses_metadata.json",
        test_code
    )
    assert len(issues) > 0, "Rule should detect unrestricted admin access (0.0.0.0/0)"

def test_restricted_admin_access():
    """Test that restricted admin access is allowed."""
    test_code = '''
admin_config = {
    "ingress_rules": [{
        "from_port": 22,
        "to_port": 22,
        "protocol": "tcp",
        "cidr_blocks": ["10.0.0.0/8", "172.16.0.0/12"]
    }]
}
'''
    issues = pgr.check_file_for_rule(
        "python_docs/administration_services_access_should_be_restricted_to_specific_ip_addresses_metadata.json",
        test_code
    )
    assert len(issues) == 0, "Rule should allow restricted admin access (private network ranges)"

def test_non_admin_unrestricted_access():
    """Test that unrestricted access in non-admin contexts is ignored."""
    test_code = '''
public_config = {
    "ingress_rules": [{
        "from_port": 80,
        "to_port": 80,
        "protocol": "tcp",
        "cidr_blocks": ["0.0.0.0/0"]
    }]
}
'''
    issues = pgr.check_file_for_rule(
        "python_docs/administration_services_access_should_be_restricted_to_specific_ip_addresses_metadata.json",
        test_code
    )
    assert len(issues) == 0, "Rule should ignore unrestricted access in non-admin contexts"