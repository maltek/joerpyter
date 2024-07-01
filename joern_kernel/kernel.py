import asyncio
import secrets
import time
import os
import tempfile
import threading

from cpgqls_client import CPGQLSClient, import_code_query, workspace_query
from ipykernel.kernelbase import Kernel

class JoernKernel(Kernel):
    binary_name = os.environ.get("JOERPYTER_BINARY", "joern")

    implementation = os.environ.get("JOERPYTER_NAME", "Joern")
    implementation_version = '1.0'
    language = 'scala'
    language_version = '0.1'
    language_info = {
        'name': 'scala',
        'mimetype': 'text/x-scala',
        'file_extension': '.sc',
    }
    banner = f"{implementation} kernel"

    client = None
    server_instance = None
    _image_file = None

    async def _run_server(self):
        if self.server_instance is None or self.server_instance.returncode is not None:
            user = secrets.token_hex(64)
            password = secrets.token_hex(64)
            port = (1 << 16) - 1 - secrets.randbits(15) # random port above 1024 (or 32767 actually)

            env = os.environ.copy()
            self._image_file = tempfile.NamedTemporaryFile(mode="r+")
            env['JOERPYTER_IMAGE_FILE'] = self._image_file.name

            with tempfile.NamedTemporaryFile("w") as script_file:
                if os.name == 'nt':
                    viewer = os.path.join(os.path.dirname(__file__), 'viewer.bat')
                else:
                    viewer = os.path.join(os.path.dirname(__file__), 'viewer.sh')
                script_file.write(f'config.tools.imageViewer = "{viewer}"\n')
                script_file.flush()

                self.server_instance = await asyncio.create_subprocess_exec(
                    self.binary_name,
                    "--server",
                    "--server-auth-username", user,
                    "--server-auth-password", password,
                    "--server-host", "localhost",
                    "--server-port", str(port),
                    "--import", script_file.name,

                    env=env)

                await asyncio.sleep(20) # bad way to wait for server to start

            if self.server_instance.returncode is not None:
                raise Exception(f"{self.binary_name} exited unexpectedly with error code {self.server_instance.returncode}")

            self.client = CPGQLSClient(f"localhost:{port}", auth_credentials=(user, password))

    def do_shutdown(self, restart):
        if self.server_instance is not None and self.server_instance.returncode is None:
            self.server_instance.kill()
            self.server_instance = None
            if self._image_file != None:
                try:
                    self._image_file.close()
                except OSError:
                    pass
                self._image_file = None

    async def do_execute(self, code, silent, store_history=True, user_expressions=None,
                   allow_stdin=False):
        try:
            await self._run_server()
            res = await self.client._send_query(code)
        except Exception as e:
            import traceback
            traceback.print_exc()
            res = {"success": "false", "stdout": "", "stderr": "connection problem: " + str(e)}

        for image in self._image_file:
            with open(image.rstrip(), "r") as img:
                info = {
                    'data': {
                        'image/svg+xml': img.read()
                    },
                    'metadata': {}
                }
                self.send_response(self.iopub_socket, 'display_data', info)
        self._image_file.seek(0)
        self._image_file.truncate()

        for stream in ("stderr", "stdout"):
            if res.get(stream) and not silent:
                stream_content = {'name': stream, 'text': res[stream] + "\n"}
                self.send_response(self.iopub_socket, 'stream', stream_content)

        return {'status': 'ok' if res['success'] else 'error',
                # The base class increments the execution count
                'execution_count': self.execution_count,
                'payload': [],
                'user_expressions': {},
               }
