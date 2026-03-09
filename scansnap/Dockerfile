ARG BUILD_FROM
FROM ${BUILD_FROM}

RUN apt-get update && apt-get install -y --no-install-recommends \
    # SANE + Fujitsu backend
    sane-utils \
    libsane \
    # OCR engine
    tesseract-ocr \
    tesseract-ocr-eng \
    # OCR pipeline (also installs ghostscript, unpaper)
    ocrmypdf \
    # Lossless TIFF→PDF assembly
    img2pdf \
    # Text extraction from OCR'd PDF
    poppler-utils \
    # Upload and HA API calls
    curl \
    # USB access for SANE and button daemon
    libusb-1.0-0 \
    # Python scripts + USB button daemon
    python3 \
    python3-usb \
    python3-pillow \
    && rm -rf /var/lib/apt/lists/*

COPY rootfs/ /

RUN chmod +x \
    /run.sh \
    /etc/scanbd/scripts/scan.sh \
    /usr/local/bin/button_daemon.py \
    /usr/local/bin/remove_blank_pages.py \
    /usr/local/bin/name_from_ocr.py

CMD ["/run.sh"]
