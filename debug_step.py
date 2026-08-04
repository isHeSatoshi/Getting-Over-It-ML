from vm_bridge.node_bridge import NodeBridge

b = NodeBridge()
print("Reset state:", b.reset())
resp = b._send_cmd({"type": "step", "command_id": 1, "nx": 0.0, "ny": 0.0, "is_down": True, "n_steps": 1})
print("Raw Step Response:", resp)
b.close()
