import pyvisa

# Initialize VISA resource manager
rm = pyvisa.ResourceManager()

# List all connected instruments
resources = rm.list_resources()
print("Connected instruments:")
for resource in resources:
    print(resource)
