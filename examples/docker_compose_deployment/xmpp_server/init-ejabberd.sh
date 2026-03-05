#!/bin/bash
# Wait for ejabberd to be ready
echo "Waiting for ejabberd to start..."
sleep 10

# Register the SMIA agent
echo "Registering smia_agent user..."
ejabberdctl register smia_agent localhost asd

# Verify registration
echo "Verifying registration..."
ejabberdctl registered_users localhost

echo "ejabberd initialization complete"
