# Use a standard Ubuntu base image
FROM ubuntu:22.04

# Set noninteractive frontend for apt-get to avoid prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies including build tools and ffmpeg
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    wget \
    git \
    ffmpeg \
    build-essential \
    cmake \
    nano \
    ca-certificates \
    python3-pip \
    python3-dev && \
    rm -rf /var/lib/apt/lists/*

# Install Miniconda
RUN wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O miniconda.sh && \
    bash miniconda.sh -b -p /opt/conda && \
    rm miniconda.sh && \
    /opt/conda/bin/conda init

# Set PATH environment variable
ENV PATH=/opt/conda/bin:$PATH
ENV MPLCONFIGDIR=/tmp/matplotlib_cache
ENV TRANSFORMERS_CACHE=/app/SoniTranslate/.cache/transformers
ENV HF_HOME=/app/SoniTranslate/.cache/huggingface
# Another common variable for Hugging Face

# Create cache directories and ensure they are writable
RUN mkdir -p $MPLCONFIGDIR $TRANSFORMERS_CACHE $HF_HOME && \
    chmod -R 777 $MPLCONFIGDIR $TRANSFORMERS_CACHE $HF_HOME

# Create conda environment and install base pip
RUN /opt/conda/bin/conda create -n sonitr python=3.10 -y && \
    echo "conda activate sonitr" >> ~/.bashrc && \
    /opt/conda/bin/conda run -n sonitr pip install pip==23.1.2

# Set working directory and clone the repository
WORKDIR /app

RUN rm -rf /app/SoniTranslate
RUN git clone https://github.com/hoangquocvietbro/SoniTranslate.git
RUN chmod -R 777 /app/SoniTranslate
# --- START SoniTranslate specific installations within the conda environment ---

# Activate conda environment for subsequent RUN commands implicitly via conda run
SHELL ["/bin/bash", "-c"]
RUN echo "Running pip installs within sonitr environment"

# Install PyTorch for CPU ONLY first
# Check https://pytorch.org/get-started/locally/ for the latest CPU command if needed
RUN /opt/conda/bin/conda run -n sonitr pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# Install requirements from files
# Note: Using -v for verbose output during debugging, can be removed for cleaner logs
RUN cd /app/SoniTranslate && /opt/conda/bin/conda run -n sonitr pip install -r requirements_base.txt -v
RUN cd /app/SoniTranslate && /opt/conda/bin/conda run -n sonitr pip install -r requirements_extra.txt -v

# Install ONNX Runtime for CPU
RUN cd /app/SoniTranslate && /opt/conda/bin/conda run -n sonitr pip install onnxruntime

# Install XTTS requirements
RUN cd /app/SoniTranslate && /opt/conda/bin/conda run -n sonitr pip install -q -r requirements_xtts.txt

# Install specific TTS version (without dependencies first, as in original)
RUN cd /app/SoniTranslate && /opt/conda/bin/conda run -n sonitr pip install -q TTS==0.21.1 --no-deps

# Uninstall and reinstall specific versions of numpy, pandas, librosa (as in original)
RUN cd /app/SoniTranslate && /opt/conda/bin/conda run -n sonitr pip uninstall -y numpy pandas librosa
RUN cd /app/SoniTranslate && /opt/conda/bin/conda run -n sonitr pip install numpy==1.23.1 pandas==1.4.3 librosa==0.10.0
RUN cd /app/SoniTranslate && /opt/conda/bin/conda run -n sonitr pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
# Install older TTS and torchcrepe versions (as in original)
# WARNING: This might conflict with TTS==0.21.1 installed earlier. Kept as per original logic.
RUN cd /app/SoniTranslate && /opt/conda/bin/conda run -n sonitr pip install "tts<0.21.0" "torchcrepe<0.0.20"

# Modify the app launch command to listen on all interfaces (as in original)
RUN sed -i '/app\.launch(/,/debug=/s/max_threads=1,/max_threads=1, server_name="0.0.0.0",/' /app/SoniTranslate/app_rvc.py

# Expose the application port
EXPOSE 7860

# Copy the entrypoint script
COPY entrypoint.sh /app/entrypoint.sh
# Ensure entrypoint script is executable
RUN chmod +x /app/entrypoint.sh

# Set final working directory
WORKDIR /app/SoniTranslate

# Define the command to run the application using the entrypoint script
# It's assumed entrypoint.sh activates the conda environment and runs the app
CMD ["/bin/bash", "-c", "/app/entrypoint.sh"]
