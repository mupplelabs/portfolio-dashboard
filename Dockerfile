# Stage 1: Build the Vue.js frontend
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Install dependencies
COPY frontend/package*.json ./
RUN npm install

# Copy frontend source code and build
COPY frontend/ .
RUN npm run build

# Stage 2: Setup the FastAPI backend
FROM python:3.11-slim

WORKDIR /app

# Install backend dependencies
# Copy only the requirements first to leverage Docker cache
COPY backend/requirements.txt backend/requirements-rag.txt* ./

ARG INSTALL_RAG=false
# Always install base requirements first to get the latest versions (like pydantic-ai)
RUN pip install --no-cache-dir -r requirements.txt
# Then install RAG requirements if requested (which may downgrade openai but leaves pydantic-ai intact)
RUN if [ "$INSTALL_RAG" = "true" ] && [ -f requirements-rag.txt ]; then \
      pip install --no-cache-dir -r requirements-rag.txt; \
    fi

# Copy the backend code
COPY backend/ .

# Ensure the data directory exists
RUN mkdir -p data

# Copy the built frontend from Stage 1 into the backend's static directory
COPY --from=frontend-builder /app/frontend/dist /app/static

# Expose the FastAPI port
EXPOSE 8000

# Run Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
