def init_app(app):
    from .views import bp
    app.register_blueprint(bp)
