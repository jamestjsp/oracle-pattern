package hessenberg

import (
	"errors"
	"math"
	"slices"
	"testing"

	"gonum.org/v1/gonum/blas"
	"gonum.org/v1/gonum/blas/blas64"
)

func matrix(rows, cols, stride int, data []float64) blas64.General {
	return blas64.General{Rows: rows, Cols: cols, Stride: stride, Data: data}
}

func TestProduct(t *testing.T) {
	for _, side := range []blas.Side{blas.Left, blas.Right} {
		for _, trans := range []blas.Transpose{blas.NoTrans, blas.Trans, blas.ConjTrans} {
			t.Run(string(side)+string(trans), func(t *testing.T) {
				m, n := 3, 2
				k := n
				if side == blas.Left {
					k = m
				}
				h := matrix(k, k, k+2, make([]float64, k*(k+2)))
				a := matrix(m, n, n+1, []float64{1, 2, 99, -3, 5, 99, 7, -11, 99})
				b := matrix(m, n, n+2, make([]float64, m*(n+2)))
				for i := range b.Data {
					b.Data[i] = 99
				}
				for i := 0; i < k; i++ {
					for j := 0; j < h.Stride; j++ {
						h.Data[i*h.Stride+j] = math.NaN()
						if j < k && i <= j+1 {
							h.Data[i*h.Stride+j] = float64(2 + i*3 - j)
						}
					}
				}
				origH, origA := slices.Clone(h.Data), slices.Clone(a.Data)
				if err := Product(side, trans, -0.5, h, a, b); err != nil {
					t.Fatal(err)
				}
				for i := 0; i < m; i++ {
					for j := 0; j < n; j++ {
						var want float64
						for q := 0; q < k; q++ {
							hr, hc, ar, ac := i, q, q, j
							if side == blas.Right {
								hr, hc, ar, ac = q, j, i, q
							}
							if trans != blas.NoTrans {
								hr, hc = hc, hr
							}
							if hr <= hc+1 {
								want += -0.5 * origH[hr*h.Stride+hc] * origA[ar*a.Stride+ac]
							}
						}
						if b.Data[i*b.Stride+j] != want {
							t.Fatalf("(%d,%d): got %g want %g", i, j, b.Data[i*b.Stride+j], want)
						}
					}
				}
				for i, v := range h.Data {
					if math.Float64bits(v) != math.Float64bits(origH[i]) {
						t.Fatal("H changed")
					}
				}
				if !slices.Equal(a.Data, origA) {
					t.Fatal("A changed")
				}
				for i, v := range b.Data {
					if i%b.Stride >= n && v != 99 {
						t.Fatal("B padding changed")
					}
				}
			})
		}
	}
}

func TestProductQuickReturns(t *testing.T) {
	h := matrix(2, 2, 2, nil)
	a := matrix(2, 3, 3, nil)
	b := matrix(2, 3, 4, []float64{math.NaN(), math.NaN(), math.NaN(), 77, math.NaN(), math.NaN(), math.NaN(), 77})
	if err := Product('l', 'c', 0, h, a, b); err != nil {
		t.Fatal(err)
	}
	if !slices.Equal(b.Data, []float64{0, 0, 0, 77, 0, 0, 0, 77}) {
		t.Fatal(b.Data)
	}
	if err := Product(blas.Left, blas.NoTrans, 1, matrix(0, 0, 1, nil), matrix(0, 4, 4, nil), matrix(0, 4, 4, nil)); err != nil {
		t.Fatal(err)
	}
	if err := Product(blas.Left, blas.NoTrans, 1, h, matrix(2, 0, 1, nil), matrix(2, 0, 1, nil)); err != nil {
		t.Fatal(err)
	}
	if err := Product('?', blas.NoTrans, 0, h, a, b); err != ArgumentError("side") {
		t.Fatalf("quick return hid invalid mode: %v", err)
	}
}

func TestProductValidation(t *testing.T) {
	tests := []struct {
		name   string
		change func(*blas64.General, *blas64.General, *blas64.General)
		want   ArgumentError
	}{
		{"negative rows", func(h, a, b *blas64.General) { a.Rows = -1 }, "rows"},
		{"negative cols", func(h, a, b *blas64.General) { a.Cols = -1 }, "cols"},
		{"h shape", func(h, a, b *blas64.General) { h.Cols = 1 }, "h"},
		{"h stride", func(h, a, b *blas64.General) { h.Stride = 1 }, "h"},
		{"a stride", func(h, a, b *blas64.General) { a.Stride = 1 }, "a"},
		{"b stride", func(h, a, b *blas64.General) { b.Stride = 1 }, "b"},
		{"b shape", func(h, a, b *blas64.General) { b.Rows = 1 }, "b"},
		{"short h", func(h, a, b *blas64.General) { h.Data = h.Data[:3] }, "h"},
		{"short a", func(h, a, b *blas64.General) { a.Data = a.Data[:3] }, "a"},
		{"short b", func(h, a, b *blas64.General) { b.Data = b.Data[:3] }, "b"},
		{"overflowing descriptor", func(h, a, b *blas64.General) {
			a.Rows = int(^uint(0) >> 1)
			h.Rows = a.Rows
			h.Cols = a.Rows
			h.Stride = a.Rows
			b.Rows = a.Rows
		}, "b"},
	}
	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			h := matrix(2, 2, 2, []float64{1, 2, 3, 4})
			a := matrix(2, 2, 2, []float64{5, 6, 7, 8})
			b := matrix(2, 2, 2, []float64{9, 10, 11, 12})
			test.change(&h, &a, &b)
			before := slices.Clone(b.Data)
			var arg ArgumentError
			err := Product(blas.Left, blas.NoTrans, 1, h, a, b)
			if !errors.As(err, &arg) || arg != test.want {
				t.Fatalf("got %v want %s", err, test.want)
			}
			if !slices.Equal(b.Data, before) {
				t.Fatal("invalid call mutated output")
			}
		})
	}
}
