FROM node:18-alpine
WORKDIR /app
COPY package.json /app/package.json
COPY package-lock.json /app/package-lock.json
RUN npm ci
COPY . /app
ENV VITE_API_BASE_URL=http://localhost:8000
EXPOSE 5173
CMD ["npm", "run", "dev"]