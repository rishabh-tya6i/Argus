FROM node:18-alpine

WORKDIR /app

# Install dependencies first for better caching
COPY package.json ./
# If package-lock.json exists, copy it as well
COPY package-lock.json* ./

RUN npm install

# Copy source code
COPY . .

# Environment variable for the API base URL (can be overridden in compose)
ENV VITE_API_BASE_URL=http://localhost:8000

# Vite dev server default port
EXPOSE 5173

# Use --host to make it accessible outside the container
CMD ["npm", "run", "dev", "--", "--host"]