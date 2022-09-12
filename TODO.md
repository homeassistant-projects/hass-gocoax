TODO: Python library that connects to an adapter and converts the binary format data
info a JSON structure. For example, something like the following:

```json
{
  "mac": "94:cc:04:12:01:0a",
  "ip": "192.168.254.254",
  "moca_ver": "2.5",
  "link_status": "up",
  "adapter_name": "LivingRoom",
  "packets": {
      "tx": {
          "ok": 12412,
          "bad": 0,
          "dropped": 0
       },
      "rx": {
          "ok": 3212,
          "bad": 0,
          "dropped": 0
       },
  },
  "network":
      "0": {
         "moca_ver": "2.5"
      },
      "1": {
         "moca_ver": "2.5"
      },
      "2": {
         "moca_ver": "2.0"
      },
  },
  "link_phy_rates": {
  }
}
```


Example API:

```python
import json
import httpx

async def async_gocoax_status(host, user, password):
      status = {
        "ip": host
      }

      async with httpx.AsyncClient(auth=(user, password)) as client:
      	    url = f"https:{host}/ms/0/0x16"
	    resp = await client.get(url)
	    # ...

      return jsons.dump(status)
```
