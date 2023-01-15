import asyncio
import secrets
import time

from cpgqls_client import CPGQLSClient, import_code_query, workspace_query
from ipykernel.kernelbase import Kernel

class JoernKernel(Kernel):
    implementation = 'Joern'
    implementation_version = '1.0'
    language = 'scala'
    language_version = '0.1'
    language_info = {
        'name': 'scala',
        'mimetype': 'text/x-scala',
        'file_extension': '.sc',
    }
    banner = "Joern kernel"

    client = None
    server_instance = None

    async def _run_server(self):
        if self.server_instance is None or self.server_instance.returncode is not None:
            user = secrets.token_hex(64)
            password = secrets.token_hex(64)
            port = (1 << 16) - 1 - secrets.randbits(15) # random port above 1024 (or 32767 actually)
            self.server_instance = await asyncio.create_subprocess_exec(
                "joern",
                "--server",
                "--server-auth-username", user,
                "--server-auth-password", password,
                "--server-host", "localhost",
                "--server-port", str(port))

            await asyncio.sleep(10) # bad way to wait for server to start
            if self.server_instance.returncode is not None:
                raise Exception(f"joern exited unexpectedly with error code {self.server_instance.returncode}")

            self.client = CPGQLSClient(f"localhost:{port}", auth_credentials=(user, password))

    def do_shutdown(self, restart):
        if self.server_instance is not None and self.server_instance.returncode is None:
            self.server_instance.kill()
            self.server_instance = None

    async def do_execute(self, code, silent, store_history=True, user_expressions=None,
                   allow_stdin=False):
        try:
            await self._run_server()
            res = await self.client._send_query(code)
        except Exception as e:
            res = {"success": "false", "stdout": "", "stderr": "connection problem: " + str(e)}

        for stream in ("stderr", "stdout"):
            if res[stream] and not silent:
                stream_content = {'name': stream, 'text': res[stream] + "\n"}
                self.send_response(self.iopub_socket, 'stream', stream_content)

        return {'status': 'ok' if res['success'] else 'error',
                # The base class increments the execution count
                'execution_count': self.execution_count,
                'payload': [],
                'user_expressions': {},
               }
