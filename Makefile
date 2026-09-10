.PHONY: verify audit

verify:
	go test ./...
	go vet ./...
	python3 -m unittest discover -s oracle -p 'test_oracle.py' -v
	python3 oracle/run.py verify

audit:
	python3 -m unittest discover -s oracle -p 'test_capture.py' -v
	python3 oracle/run.py audit
