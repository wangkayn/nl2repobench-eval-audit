ARG BASE_IMAGE
FROM --platform=linux/amd64 ${BASE_IMAGE}

# Match NL2RepoBench's generated evaluation image: the sanitized candidate
# workspace overlays the hidden-test base image.
COPY workspace /workspace
WORKDIR /workspace
ENV PYTHONPATH=/workspace:$PYTHONPATH
CMD ["tail", "-f", "/dev/null"]
