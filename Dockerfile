FROM python:3.12-slim

WORKDIR /app

# Copy everything
COPY server/pyproject.toml ./server/
COPY server/app/ ./server/app/

# Install dependencies
RUN pip install --no-cache-dir $(python3 -c "\
import tomllib; \
d = tomllib.load(open('server/pyproject.toml','rb')); \
print(' '.join(d.get('project',{}).get('dependencies',[])))") reportlab

# Copy storefront
COPY index.html shop.html product.html checkout.html about.html \
     blog.html contact.html account.html track.html wishlist.html ./
COPY css/ ./css/
COPY js/ ./js/

# Create data + uploads dirs
RUN mkdir -p server/data server/uploads

EXPOSE 8013

WORKDIR /app/server
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8013"]
