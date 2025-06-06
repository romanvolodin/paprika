#!/bin/bash

PROJECT_DIR="~/paprika"
REPO_DIR="~/backup/paprika_dumpdata"

cd "$PROJECT_DIR" || exit 1

docker compose exec paprika-app ./manage.py dumpdata \
 --format=json \
 --indent=2 \
 --natural-primary \
 --natural-foreign \
 --exclude sessions.session \
 --exclude auth.permission \
 --exclude admin.logentry \
 --exclude contenttypes \
 > "$REPO_DIR"/dump.json

cd "$REPO_DIR" || exit 1
git add .
git commit -m "Automated backup" || echo "No changes to commit"
git push
