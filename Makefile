.PHONY: build deploy

build:
	sam build --use-container

deploy:
	sam deploy --guided