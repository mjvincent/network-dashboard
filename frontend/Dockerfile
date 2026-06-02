# 1. Build stage
FROM node:22.12-alpine AS build-stage

WORKDIR /app

RUN echo "Debug: Creating .debug-file in /app" > .debug-file

# Install dependencies only
COPY package.json package-lock.json* ./
RUN echo "Dependencies copied" && npm install

# Copy source code and config
COPY src/ ./src/
COPY index.html vite.config.js ./

# SAFETY STEP: Ensure the App.jsx file is complete and has proper line endings
# We use 'sed' to strip potential Windows carriage returns (\r) and ensure a clean export
RUN echo "App.jsx processing" && sed -i 's/\r$//' src/App.jsx && \
    if ! grep -q "export default App" src/App.jsx; then \
      echo "export default App;" >> src/App.jsx; \
    fi

# Clean cache to prevent stale builds and run the production build
RUN echo "Running npm build" && rm -rf node_modules/.vite && npm run build

# 2. Production stage
FROM nginx:stable-alpine AS production-stage
COPY --from=build-stage /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]