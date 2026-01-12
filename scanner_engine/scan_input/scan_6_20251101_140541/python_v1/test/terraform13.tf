# Configure the AzureRM provider (required in TF configs)
provider "azurerm" {
  features {}
}

# Example Resource Group
resource "azurerm_resource_group" "example" {
  name     = "example-resources"
  location = "East US"
}

# 🚨 Vulnerable Role Assignment (triggers the rule)
resource "azurerm_role_assignment" "bad_example" {
  scope                = azurerm_resource_group.example.id
  role_definition_name = "Owner"   # 🚨 Forbidden value -> will trigger rule
  principal_id         = "00000000-0000-0000-0000-000000000000" # Example Object ID
}
