# The only image untrusted analysis code ever runs in. There is no network at runtime,
# so the whole stats stack is baked in, at pinned versions every receipt can cite.
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /usr/local/bin/uv
RUN uv pip install --system --no-cache \
    pandas==2.2.3 numpy==2.1.3 scipy==1.14.1 statsmodels==0.14.4 matplotlib==3.9.2
RUN useradd -u 1000 -m sandbox
ENV MPLCONFIGDIR=/tmp/mpl PYTHONDONTWRITEBYTECODE=1
USER 1000
WORKDIR /tmp
