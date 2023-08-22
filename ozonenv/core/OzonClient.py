import logging
import aiofiles
import aiohttp
import httpx

logger = logging.getLogger("asyncio")


class OzonClient:
    @classmethod
    def create(cls, apikey, is_api=False, url="http://client:8526"):
        self = OzonClient()
        self.default_url = url
        self.is_api = is_api
        self.api_key = apikey
        return self

    def get_headers(self):
        header = {
            "authtoken": f"{self.api_key}",
            "accept": "application/json",
            "content-type": "application/json",
        }
        if self.is_api:
            header.pop("authtoken")
            header["apitoken"] = self.api_key
        return header.copy()

    async def delete_attachment(self, field_key, model, rec_name, data):
        url = f"{self.default_url}/client/attachment/trash/{model}/{rec_name}"
        data_obj = {
            "field": field_key,
            "key": data.get("key"),
            "filename": data.get("filename"),
            "file_path": data.get("file_path"),
        }
        headers = self.get_headers()
        result = {"status": "ok"}
        async with httpx.AsyncClient(timeout=None) as client:
            res = await client.post(url, json=data_obj, headers=headers)
            if res:
                res = res.json()
                if isinstance(res, list) and len(res) > 0:
                    r = res[0]
                    if r.get("status") == "error":
                        result["status"] = "error"
                        return result
                return result
            else:
                return {"status": "error", "message": res}

    async def delete_attachments(self, form_data, model, attachment_key):
        rec_name = form_data.get("rec_name")
        attachments = form_data.get(attachment_key)
        result = {"status": "ok", "message": "done"}
        for attachment in attachments:
            res = await self.delete_attachment(
                attachment_key, model, rec_name, attachment
            )
            if res.get("status") == "error":
                result["message"] = (
                    f"Error delete file"
                    f" {attachment['filename']} "
                    f"key {attachment['key']}"
                )
                result["status"] = "error"
                return result
        return result

    async def send_mail(self, model, rec_name, tmp_name):
        url = (
            f"{self.default_url}/client/send/"
            f"mail/{model}/{rec_name}/{tmp_name}"
        )
        data_obj = {}
        headers = self.get_headers()
        result = {"status": "ok"}
        async with httpx.AsyncClient(timeout=None) as client:
            res = await client.post(url, json=data_obj, headers=headers)
            if res:
                res = res.json()
                if isinstance(res, list) and len(res) > 0:
                    r = res[0]
                    if r.get("status") == "error":
                        result["status"] = "error"
                        return result
                return result
            else:
                return {"status": "error", "message": res}

    async def post_form_with_file(
        self, url, headers, form_data: dict = None, files: list = None
    ):
        if files is None:
            files = []
        if form_data is None:
            form_data = {}
        files_to_send = []
        headers.pop('content-type')
        for f_todo in files:
            f = await aiofiles.open(f_todo['file_path'], 'rb')
            data = await f.read()
            files_to_send.append((f_todo['file_key'], data))
        client = httpx.AsyncClient(timeout=10)
        return await client.post(
            url,
            files=files_to_send,
            data={'formObj': json.dumps(form_data)},
            headers=headers,
        )

    async def post_form_data(self, url, headers, form_data: dict = None):
        if form_data is None:
            form_data = {}
        client = httpx.AsyncClient(timeout=10)
        return await client.post(
            url, data={'formObj': json.dumps(form_data)}, headers=headers
        )

    async def post_form(
        self, action_name, model, form_data: dict = None, files: list = None
    ):
        if files is None:
            files = []
        if form_data is None:
            form_data = {}
        url = f"{self.default_url}/" f"action/{action_name}"
        if form_data.get("rec_name"):
            url = f"{url}/{form_data.get('rec_name')}"
        headers = self.get_headers()
        form_data['data_model'] = model
        if files:
            res = await self.post_form_with_file(
                url, headers, form_data, files
            )
        else:
            res = await self.post_form_data(url, headers, form_data)
        result = {"status": "ok"}
        if res:
            res = res.json()
            if isinstance(res, list) and len(res) > 0:
                r = res[0]
                if r.get("status") == "error":
                    result["status"] = "error"
                    return result
            return result
        else:
            return {"status": "error", "message": res}

    async def copy_attachments(
        self,
        model: str,
        rec_name: str,
        field: str,
        dest: str,
    ) -> dict:
        url = (
            f"{self.default_url}/client/attachment/"
            f"copy/{model}/{rec_name}/{field}/{dest}"
        )
        headers = self.get_headers()
        async with httpx.AsyncClient(timeout=None) as client:
            res = await client.post(url, json={}, headers=headers)
            if res:
                return res
            else:
                return {"status": "error", "message": res}

    async def unlink_attachment(self, field_key, model, rec_name, data):
        url = (
            f"{self.default_url}/client/"
            f"attachment/unlink/{model}/{rec_name}"
        )
        data_obj = {
            "field": field_key,
            "key": data.get("key"),
            "filename": data.get("filename"),
            "file_path": data.get("file_path"),
        }
        headers = self.get_headers()
        result = {"status": "ok"}
        async with httpx.AsyncClient(timeout=None) as client:
            res = await client.post(url, json=data_obj, headers=headers)
            if res:
                res = res.json()
                if isinstance(res, list) and len(res) > 0:
                    r = res[0]
                    if r.get("status") == "error":
                        result["status"] = "error"
                        return result
                return result
            else:
                return {"status": "error", "message": res}


class LabelPrinter:
    @classmethod
    def create(cls, apikey="", is_api=False, url=""):
        self = LabelPrinter()
        self.default_url = url
        self.is_api = is_api
        self.api_key = apikey
        return self

    def get_headers(self):
        header = {
            "authtoken": f"{self.api_key}",
            "accept": "application/json",
            "content-type": "application/json",
        }
        if self.is_api:
            header.pop("authtoken")
            header["apitoken"] = self.api_key
        return header.copy()

    async def status(
        self,
    ):
        url = f"{self.default_url}/status"
        logger.info(url)
        headers = self.get_headers()

        try:
            async with aiohttp.ClientSession() as client:
                async with client.get(url, headers=headers) as resp:
                    return await resp.json()
        except Exception as e:
            logger.error(e, exc_info=True)
            return {"status": "error", "message": str(e)}

    async def print_label(self, payload):
        url = f"{self.default_url}/print_label"
        logger.info(url)
        headers = self.get_headers()

        try:
            async with aiohttp.ClientSession() as client:
                async with client.post(
                    url, json=payload, headers=headers
                ) as resp:
                    return await resp.json()
        except Exception as e:
            logger.error(e, exc_info=True)
            return {"status": "error", "message": str(e)}
