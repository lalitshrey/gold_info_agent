from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from flask import Flask, jsonify, render_template, request

# Reuse the existing news aggregation logic from the FastAPI module
from .app import get_news  # noqa: F401


_BASE_DIR = Path(__file__).parent
_TEMPLATES_DIR = _BASE_DIR / "templates"
_STATIC_DIR = _BASE_DIR / "static"


def create_app() -> Flask:
    static_folder = str(_STATIC_DIR) if _STATIC_DIR.exists() else None
    app = Flask(
        __name__,
        template_folder=str(_TEMPLATES_DIR),
        static_folder=static_folder,
        static_url_path="/static" if static_folder else None,
    )

    @app.get("/")
    def index():
        tickers_param: Optional[str] = request.args.get("tickers")
        limit: int = int(request.args.get("limit", 20))
        days: int = int(request.args.get("days", 7))

        symbols: List[str] = []
        articles: List[Dict] = []
        if tickers_param:
            symbols = [
                t.strip().upper()
                for t in tickers_param.split(",")
                if t.strip()
            ]
            if symbols:
                articles = get_news(
                    symbols,
                    per_source_limit=max(1, min(limit, 100)),
                    google_days=max(1, min(days, 30)),
                )

        # Flask templates can access `request` implicitly, but we pass values
        # explicitly
        return render_template(
            "index.html",
            request=request,
            tickers=tickers_param or "",
            limit=limit,
            days=days,
            symbols=symbols,
            articles=articles,
        )

    @app.get("/news")
    def news_endpoint():
        tickers_param: Optional[str] = request.args.get("tickers")
        if not tickers_param:
            return jsonify({"detail": "No tickers provided"}), 400

        limit: int = int(request.args.get("limit", 20))
        days: int = int(request.args.get("days", 7))
        symbols = [
            t.strip().upper()
            for t in tickers_param.split(",")
            if t.strip()
        ]
        if not symbols:
            return jsonify({"detail": "No tickers provided"}), 400

        articles = get_news(
            symbols,
            per_source_limit=max(1, min(limit, 100)),
            google_days=max(1, min(days, 30)),
        )
        return jsonify(
            {"tickers": symbols, "count": len(articles), "articles": articles}
        )

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8002)
