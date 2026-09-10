package main

import (
	"math"
	"testing"
)

func TestWireStorage(t *testing.T) {
	values := []string{"1", "-0", "NaN", "4", "5", "6"}
	a, err := pack(2, 3, 2, values)
	if err != nil {
		t.Fatal(err)
	}
	if !padding(a) || a.Data[0] != 1 || !math.Signbit(a.Data[1]) || !math.IsNaN(a.Data[2]) || a.Data[a.Stride] != 4 {
		t.Fatal("incorrect row-major pack")
	}
	got := unpack(a)
	for i := range values {
		if values[i] != got[i] {
			t.Fatalf("roundtrip %d: %s != %s", i, values[i], got[i])
		}
	}
	a.Data[3] = 0
	if padding(a) {
		t.Fatal("missed damaged row padding")
	}
	if _, err := pack(2, 3, 0, values[:5]); err == nil {
		t.Fatal("accepted truncated input")
	}
}
