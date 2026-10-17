# Godot MCP lab: Godot 4.7.2 (official Linux build, checked against the release's SHA512-SUMS), the community
# godot-editor-mcp server (PyPI, pinned) and its editor add-on (GitHub release, pinned). Lab snapshot 17 Oct 2026.
# Nothing is installed on the host. The editor runs headless inside the container.
FROM python:3.12-slim-bookworm
ARG GODOT=4.7.2-stable
ARG GODOT_ZIP=Godot_v4.7.2-stable_linux.x86_64.zip
ARG MCP_VERSION=2026.10.15
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl unzip libfontconfig1 \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /tmp/dl
RUN curl -fsSLO "https://github.com/godotengine/godot/releases/download/${GODOT}/${GODOT_ZIP}" \
 && curl -fsSLO "https://github.com/godotengine/godot/releases/download/${GODOT}/SHA512-SUMS.txt" \
 && grep " ${GODOT_ZIP}\$" SHA512-SUMS.txt > check.txt && test "$(wc -l < check.txt)" = 1 && sha512sum -c check.txt \
 && unzip -q "${GODOT_ZIP}" -d /opt/godot && mv /opt/godot/Godot_v4.7.2-stable_linux.x86_64 /opt/godot/godot \
 && chmod +x /opt/godot/godot && cp check.txt /opt/godot/ \
 && curl -fsSL -o /opt/godot_mcp_addon.zip "https://github.com/hybridindie/godot-mcp/releases/download/${MCP_VERSION}/godot_mcp_addon.zip" \
 && sha256sum /opt/godot_mcp_addon.zip > /opt/godot_mcp_addon.sha256 \
 && cd / && rm -rf /tmp/dl
ENV PATH=/opt/godot:$PATH
RUN pip install --no-cache-dir "godot-editor-mcp==${MCP_VERSION}" pytest && pip freeze > /opt/pip-freeze.txt
WORKDIR /work
