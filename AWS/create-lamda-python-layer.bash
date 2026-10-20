# 1. Clean up old files
rm -rf python lambda_layer.zip
mkdir python

# 2. Force download of Python 3.14, Amazon Linux x86_64 binaries
pip install Pillow reportlab pypdf \
  --platform manylinux2014_x86_64 \
  --target=python \
  --implementation cp \
  --python-version 3.14 \
  --only-binary=:all:

# 3. Zip and Publish for Python 3.14
zip -q -r lambda_layer.zip python

aws lambda publish-layer-version \
  --layer-name PdfWatermarkLayer-Py314 \
  --zip-file fileb://lambda_layer.zip \
  --compatible-runtimes python3.14