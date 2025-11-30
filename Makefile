.PHONY: help install install-dev test lint format clean run

help:
	@echo "Merter'in Terminali - Portföy Yönetim Sistemi"
	@echo ""
	@echo "Kullanılabilir komutlar:"
	@echo "  make install      - Production bağımlılıklarını yükle"
	@echo "  make install-dev  - Development bağımlılıklarını yükle"
	@echo "  make test         - Testleri çalıştır"
	@echo "  make lint         - Kod kalitesi kontrolü (flake8, mypy)"
	@echo "  make format       - Kod formatla (black)"
	@echo "  make clean        - Geçici dosyaları temizle"
	@echo "  make run          - Uygulamayı başlat"
	@echo "  make setup        - Pre-commit hooks kurulumu"

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements.txt
	pip install pre-commit
	pre-commit install

test:
	pytest tests/ -v --cov=. --cov-report=term-missing

test-fast:
	pytest tests/ -v -m "not slow"

lint:
	flake8 . --max-line-length=100 --extend-ignore=E203,W503
	mypy . --ignore-missing-imports --no-strict-optional

format:
	black . --line-length=100

format-check:
	black . --line-length=100 --check

clean:
	find . -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type d -name "*.egg-info" -exec rm -r {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -r {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -r {} + 2>/dev/null || true
	rm -rf build/ dist/ .eggs/

run:
	streamlit run portfoy.py

setup:
	pip install pre-commit
	pre-commit install

logs-clean:
	rm -rf logs/*.log

all: clean install-dev format lint test
