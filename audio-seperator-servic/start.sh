#!/bin/bash

# Quick Start Script for Audio Separator Service

echo "🎵 Audio Separator Service - Quick Start"
echo "========================================"

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating from template..."
    cp .env.example .env
    echo "📝 Please edit .env and add your API keys!"
    echo "   - ASSEMBLYAI_API_KEY"
    echo "   - GROQ_API_KEY"
    read -p "Press Enter after editing .env..."
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose not found. Please install Docker Compose first."
    exit 1
fi

echo ""
echo "🐳 Starting Docker containers..."
docker-compose up --build -d

echo ""
echo "⏳ Waiting for service to be ready..."
sleep 5

# Health check
for i in {1..10}; do
    if curl -s http://localhost:5000/health > /dev/null; then
        echo "✅ Service is healthy!"
        echo ""
        echo "🎉 Audio Separator Service is running!"
        echo "   - Service URL: http://localhost:5000"
        echo "   - Health Check: http://localhost:5000/health"
        echo "   - API Endpoint: http://localhost:5000/process-audio"
        echo ""
        echo "📊 View logs: docker-compose logs -f"
        echo "🛑 Stop service: docker-compose down"
        exit 0
    fi
    echo "   Attempt $i/10..."
    sleep 3
done

echo "❌ Service failed to start. Check logs:"
echo "   docker-compose logs"
exit 1
