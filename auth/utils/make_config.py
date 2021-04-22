import toml

config = {
    "atlas-username": "dbtesting",
    "atlas-password": "9bsvzutjWZfjgaxE",
    "connection-uri": "mongodb+srv://{username}:{password}@cluster0.wjvcq.mongodb.net/{default_database}?retryWrites=true&w=majority",
    "default-database": "auth_db",
    "secret": "9e9db18a0160cf4549453b4613e48fa21f537f015c6f50ddb0a7e2180debf383",
}

with open("db-config.toml", "w") as f:
    toml.dump(config, f)
