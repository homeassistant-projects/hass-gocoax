#!/usr/bin/env python3

import json
import httpx
import asyncio

# may need to deal with:
#  - csrf_token cookie and X-CSRF-TOKEN

async def async_gocoax_status(host, user='admin', password='gocoax'):
      status = {
        "ip": host
      }

      async with httpx.AsyncClient(auth=(user, password)) as client:
            url = f"http://{host}/"
            print(f"Fetching {url}")
            r = await client.get(url)
            print(r.text)

            url = f"http://{host}/ms/0/0x16"
            print(f"Fetching {url}")
            r = await client.post(url, data=json.dumps({"data":[2]}))
            print(r)
            # ...

      j = json.dumps(status)
      print(j)
      return j



loop = asyncio.get_event_loop()
tasks = [ loop.create_task(async_gocoax_status('10.1.70.5')) ]
loop.run_until_complete(asyncio.wait(tasks))
loop.close()

