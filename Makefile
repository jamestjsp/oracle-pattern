.PHONY: verify

verify:
	go test ./...
	go vet ./...
	python3 -m unittest discover -s oracle -p 'test_*.py' -v
	python3 oracle/run.py --seed 20260910 --random-cases 400 --report artifacts/acceptance.json
	python3 oracle/run.py --seed 20260911 --random-cases 400 --report artifacts/fresh-seed.json
	python3 oracle/run.py --replay artifacts/acceptance.json --case asymmetric-LT --report artifacts/replay.json
