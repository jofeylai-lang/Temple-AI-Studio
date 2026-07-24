from __future__ import annotations

import json
import mimetypes
import shutil
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any


class ProviderExecutionError(RuntimeError):
    pass


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def create_comfy_workflow_descriptor(
    source: Path,
    output: Path,
    descriptor_id: str,
    provider_id: str,
    bindings: dict[str, dict[str, str] | list[dict[str, str]]],
    required_bindings: list[str],
    version: str = "1.0.0",
) -> dict[str, Any]:
    graph = json.loads(Path(source).read_text(encoding="utf-8-sig"))
    if not isinstance(graph, dict) or not graph:
        raise ValueError("ComfyUI API workflow must be a non-empty JSON object.")
    invalid = [
        node_id
        for node_id, node in graph.items()
        if not isinstance(node, dict) or not node.get("class_type")
    ]
    if invalid:
        raise ValueError(
            "Source is not an API-format ComfyUI workflow; invalid nodes: "
            + ", ".join(invalid[:10])
        )
    for name, binding in bindings.items():
        targets = binding if isinstance(binding, list) else [binding]
        for target in targets:
            node_id = str(target["node"])
            input_name = target["input"]
            if node_id not in graph:
                raise ValueError(f"Binding {name} references missing node {node_id}.")
            if input_name not in graph[node_id].get("inputs", {}):
                raise ValueError(
                    f"Binding {name} references missing input {node_id}.{input_name}."
                )
            current = graph[node_id]["inputs"][input_name]
            if name == "seed":
                replacement: Any = 0
            elif name == "output_prefix":
                replacement = "TempleAIStudio/production"
            elif isinstance(current, str):
                replacement = ""
            elif isinstance(current, bool):
                replacement = False
            elif isinstance(current, (int, float)):
                replacement = 0
            else:
                replacement = None
            graph[node_id]["inputs"][input_name] = replacement
    missing = sorted(set(required_bindings) - set(bindings))
    if missing:
        raise ValueError(
            "Required bindings have no target: " + ", ".join(missing)
        )
    descriptor = {
        "schema": "temple-ai-studio.comfyui-production-workflow.v1",
        "id": descriptor_id,
        "version": version,
        "providerId": provider_id,
        "productionReady": True,
        "source": str(Path(source).resolve()),
        "requiredBindings": required_bindings,
        "bindings": bindings,
        "graph": graph,
    }
    atomic_write_json(Path(output), descriptor)
    return descriptor


class ComfyUIProductionClient:
    """Minimal local ComfyUI API client for real workflow execution."""

    def __init__(self, endpoint: str = "http://127.0.0.1:8188", timeout: float = 30.0):
        self.endpoint = endpoint.rstrip("/")
        self.timeout = timeout

    def health(self) -> dict[str, Any]:
        return self._json_request("GET", "/system_stats")

    def object_info(self) -> dict[str, Any]:
        return self._json_request("GET", "/object_info")

    def upload_image(self, path: Path, subfolder: str = "temple-ai-studio") -> dict[str, Any]:
        source = Path(path)
        if not source.is_file():
            raise FileNotFoundError(str(source))
        boundary = f"----TempleAIStudio{uuid.uuid4().hex}"
        content_type = mimetypes.guess_type(source.name)[0] or "application/octet-stream"
        parts = [
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="image"; filename="{source.name}"\r\n'
            f"Content-Type: {content_type}\r\n\r\n".encode("utf-8")
            + source.read_bytes()
            + b"\r\n",
            (
                f"--{boundary}\r\n"
                'Content-Disposition: form-data; name="type"\r\n\r\n'
                "input\r\n"
            ).encode("utf-8"),
            (
                f"--{boundary}\r\n"
                'Content-Disposition: form-data; name="subfolder"\r\n\r\n'
                f"{subfolder}\r\n"
            ).encode("utf-8"),
            (
                f"--{boundary}\r\n"
                'Content-Disposition: form-data; name="overwrite"\r\n\r\n'
                "false\r\n"
            ).encode("utf-8"),
            f"--{boundary}--\r\n".encode("utf-8"),
        ]
        request = urllib.request.Request(
            f"{self.endpoint}/upload/image",
            data=b"".join(parts),
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
                name = payload.get("name", source.name)
                folder = str(payload.get("subfolder", "")).strip("/\\")
                payload["comfyPath"] = f"{folder}/{name}" if folder else name
                return payload
        except urllib.error.URLError as error:
            raise ProviderExecutionError(f"ComfyUI image upload failed: {error}") from error

    def submit(self, graph: dict[str, Any], client_id: str | None = None) -> str:
        payload = {"prompt": graph, "client_id": client_id or f"temple-{uuid.uuid4().hex}"}
        response = self._json_request("POST", "/prompt", payload)
        if response.get("node_errors"):
            raise ProviderExecutionError(
                "ComfyUI rejected the workflow: "
                + json.dumps(response["node_errors"], ensure_ascii=False)
            )
        prompt_id = response.get("prompt_id")
        if not prompt_id:
            raise ProviderExecutionError(f"ComfyUI returned no prompt id: {response}")
        return prompt_id

    def wait(self, prompt_id: str, timeout: float = 1800.0, poll_seconds: float = 1.0) -> dict[str, Any]:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            history = self._json_request("GET", f"/history/{urllib.parse.quote(prompt_id)}")
            record = history.get(prompt_id)
            if record:
                status = record.get("status", {})
                if status.get("status_str") == "error":
                    raise ProviderExecutionError(
                        "ComfyUI workflow failed: "
                        + json.dumps(status, ensure_ascii=False)
                    )
                if record.get("outputs") and status.get("completed", True):
                    return record
            time.sleep(poll_seconds)
        raise TimeoutError(f"ComfyUI workflow timed out after {timeout} seconds: {prompt_id}")

    def run_descriptor(
        self,
        descriptor_path: Path,
        values: dict[str, Any],
        output_dir: Path,
        timeout: float = 1800.0,
    ) -> dict[str, Any]:
        descriptor = json.loads(Path(descriptor_path).read_text(encoding="utf-8-sig"))
        if descriptor.get("productionReady") is not True:
            raise ProviderExecutionError("Workflow descriptor is not approved for production.")
        graph = json.loads(json.dumps(descriptor.get("graph", {})))
        if not graph:
            raise ProviderExecutionError("Workflow descriptor has no API-format graph.")
        bindings = descriptor.get("bindings", {})
        missing = sorted(set(descriptor.get("requiredBindings", [])) - set(values))
        if missing:
            raise ProviderExecutionError(f"Missing workflow bindings: {', '.join(missing)}")
        for name, value in values.items():
            binding = bindings.get(name)
            if not binding:
                continue
            targets = binding if isinstance(binding, list) else [binding]
            for target in targets:
                node_id = str(target["node"])
                input_name = target["input"]
                if node_id not in graph:
                    raise ProviderExecutionError(
                        f"Workflow binding references missing node {node_id}."
                    )
                graph[node_id].setdefault("inputs", {})[input_name] = value
        prompt_id = self.submit(graph)
        record = self.wait(prompt_id, timeout=timeout)
        artifacts = self.download_outputs(record, Path(output_dir))
        result = {
            "schema": "temple-ai-studio.real-provider-execution.v1",
            "provider": "comfyui-local",
            "provenance": "real-production",
            "workflowId": descriptor.get("id"),
            "workflowVersion": descriptor.get("version"),
            "promptId": prompt_id,
            "artifacts": artifacts,
            "history": record,
        }
        atomic_write_json(Path(output_dir) / "provider-execution.json", result)
        return result

    def download_outputs(self, record: dict[str, Any], output_dir: Path) -> list[dict[str, Any]]:
        output_dir.mkdir(parents=True, exist_ok=True)
        artifacts = []
        for node_id, output in record.get("outputs", {}).items():
            for media_key in ("images", "videos", "audio", "gifs"):
                for item in output.get(media_key, []):
                    filename = item.get("filename")
                    if not filename:
                        continue
                    query = urllib.parse.urlencode(
                        {
                            "filename": filename,
                            "subfolder": item.get("subfolder", ""),
                            "type": item.get("type", "output"),
                        }
                    )
                    target = output_dir / Path(filename).name
                    with urllib.request.urlopen(
                        f"{self.endpoint}/view?{query}",
                        timeout=self.timeout,
                    ) as response:
                        target.write_bytes(response.read())
                    artifacts.append(
                        {
                            "nodeId": node_id,
                            "mediaType": media_key,
                            "path": str(target),
                            "bytes": target.stat().st_size,
                        }
                    )
        if not artifacts:
            raise ProviderExecutionError("ComfyUI completed but returned no downloadable output.")
        return artifacts

    def _json_request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = urllib.request.Request(
            f"{self.endpoint}{path}",
            data=data,
            headers={"Content-Type": "application/json"},
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            details = error.read().decode("utf-8", errors="replace")
            raise ProviderExecutionError(
                f"ComfyUI request failed ({path}) with HTTP {error.code}: {details[-4000:]}"
            ) from error
        except urllib.error.URLError as error:
            raise ProviderExecutionError(f"ComfyUI request failed ({path}): {error}") from error


class Qwen3TTSProductionClient:
    """Runs the isolated Qwen3-TTS worker with no network fallback."""

    def __init__(self, python: Path, worker: Path, model_path: Path):
        self.python = Path(python)
        self.worker = Path(worker)
        self.model_path = Path(model_path)

    def health(self) -> dict[str, Any]:
        checks = [
            {"name": "python", "ok": self.python.is_file(), "path": str(self.python)},
            {"name": "worker", "ok": self.worker.is_file(), "path": str(self.worker)},
            {"name": "model", "ok": self.model_path.is_dir(), "path": str(self.model_path)},
        ]
        if self.python.is_file():
            result = subprocess.run(
                [str(self.python), "-c", "import qwen_tts, soundfile, torch"],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            checks.append(
                {
                    "name": "runtime-imports",
                    "ok": result.returncode == 0,
                    "reason": result.stderr[-500:] if result.returncode else "",
                }
            )
        return {"overall": "PASS" if all(check["ok"] for check in checks) else "FAIL", "checks": checks}

    def synthesize(
        self,
        text: str,
        reference_audio: Path,
        reference_text: str,
        output: Path,
        language: str = "Chinese",
        timeout: float = 1800.0,
    ) -> dict[str, Any]:
        health = self.health()
        if health["overall"] != "PASS":
            raise ProviderExecutionError(f"Qwen3-TTS is not ready: {health}")
        if not text.strip() or not reference_text.strip():
            raise ValueError("Text and exact reference transcript are required.")
        output = Path(output)
        output.parent.mkdir(parents=True, exist_ok=True)
        command = [
            str(self.python),
            str(self.worker),
            "--model",
            str(self.model_path),
            "--text",
            text,
            "--language",
            language,
            "--reference-audio",
            str(Path(reference_audio)),
            "--reference-text",
            reference_text,
            "--output",
            str(output),
            "--offline",
        ]
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        if result.returncode != 0 or not output.is_file():
            raise ProviderExecutionError(
                f"Qwen3-TTS failed with code {result.returncode}: {result.stderr[-1000:]}"
            )
        try:
            details = json.loads(result.stdout)
        except json.JSONDecodeError:
            details = {"stdout": result.stdout[-1000:]}
        return {
            "schema": "temple-ai-studio.real-voice-execution.v1",
            "provider": "qwen3-tts-local",
            "provenance": "real-production",
            "artifact": str(output),
            "bytes": output.stat().st_size,
            "details": details,
        }


class LocalCommandProductionClient:
    """Executes an approved command descriptor without invoking a shell."""

    def run_descriptor(
        self,
        descriptor_path: Path,
        values: dict[str, Any],
        output_dir: Path,
        timeout: float = 1800.0,
    ) -> dict[str, Any]:
        descriptor_path = Path(descriptor_path).resolve()
        descriptor = json.loads(descriptor_path.read_text(encoding="utf-8-sig"))
        if descriptor.get("productionReady") is not True:
            raise ProviderExecutionError("Command descriptor is not approved for production.")
        command_template = descriptor.get("command")
        if not isinstance(command_template, list) or not command_template:
            raise ProviderExecutionError("Command descriptor must contain a non-empty command list.")
        missing = sorted(set(descriptor.get("requiredBindings", [])) - set(values))
        if missing:
            raise ProviderExecutionError(f"Missing command bindings: {', '.join(missing)}")
        allowed_roots = [
            Path(item).resolve() for item in descriptor.get("allowedExecutableRoots", [])
        ]
        command = [
            self._format_argument(str(argument), values) for argument in command_template
        ]
        executable = Path(command[0]).resolve()
        if allowed_roots and not any(
            executable == root or root in executable.parents for root in allowed_roots
        ):
            raise ProviderExecutionError(
                f"Executable is outside approved roots: {executable}"
            )
        if not executable.is_file():
            raise ProviderExecutionError(f"Executable does not exist: {executable}")
        output_dir = Path(output_dir).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        started = time.perf_counter()
        result = subprocess.run(
            command,
            cwd=str(
                Path(
                    self._format_argument(
                        str(descriptor.get("workingDirectory", descriptor_path.parent)),
                        values,
                    )
                ).resolve()
            ),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
        log_path = output_dir / "provider-command.log"
        log_path.write_text(
            "COMMAND\n"
            + json.dumps(command, ensure_ascii=False)
            + "\n\nSTDOUT\n"
            + result.stdout
            + "\n\nSTDERR\n"
            + result.stderr,
            encoding="utf-8",
        )
        if result.returncode != 0:
            raise ProviderExecutionError(
                f"Production command failed with code {result.returncode}; see {log_path}."
            )
        artifacts = []
        for item in descriptor.get("outputs", []):
            rendered = Path(self._format_argument(str(item["path"]), values)).resolve()
            if not rendered.is_file() or rendered.stat().st_size <= 0:
                raise ProviderExecutionError(
                    f"Expected production output is missing or empty: {rendered}"
                )
            artifacts.append(
                {
                    "mediaType": item.get("mediaType", "file"),
                    "path": str(rendered),
                    "bytes": rendered.stat().st_size,
                }
            )
        if not artifacts:
            raise ProviderExecutionError("Command descriptor declares no output artifacts.")
        payload = {
            "schema": "temple-ai-studio.real-command-execution.v1",
            "provider": descriptor.get("providerId"),
            "provenance": "real-production",
            "descriptorId": descriptor.get("id"),
            "descriptorVersion": descriptor.get("version"),
            "durationSeconds": round(time.perf_counter() - started, 3),
            "artifacts": artifacts,
            "log": str(log_path),
        }
        atomic_write_json(output_dir / "provider-execution.json", payload)
        return payload

    @staticmethod
    def _format_argument(template: str, values: dict[str, Any]) -> str:
        try:
            return template.format_map({key: str(value) for key, value in values.items()})
        except KeyError as error:
            raise ProviderExecutionError(
                f"Command descriptor references an unknown binding: {error.args[0]}"
            ) from error
