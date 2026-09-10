// Package hessenberg implements matrix operations translated from SLICOT.
package hessenberg

import (
	"gonum.org/v1/gonum/blas"
	"gonum.org/v1/gonum/blas/blas64"
)

// ArgumentError identifies an invalid argument or matrix descriptor.
type ArgumentError string

func (e ArgumentError) Error() string { return "hessenberg: invalid " + string(e) }

// Product writes alpha*op(H)*A (Left) or alpha*A*op(H) (Right) into B.
// H is square and upper Hessenberg; elements below its subdiagonal are ignored.
// Matrices use Gonum row-major storage. A and H are unchanged, and B's padding
// is untouched. B must not overlap A or H. The transpose may be NoTrans, Trans,
// or ConjTrans (equivalent to Trans for real matrices); lowercase flags work too.
// Descriptors are validated before quick returns. Empty products access no data;
// alpha == 0 requires only B's storage. No workspace is required from callers.
//
// This is a translation of SLICOT MB01UD. See NOTICE and LICENSE-SLICOT.
func Product(side blas.Side, trans blas.Transpose, alpha float64, h, a, b blas64.General) error {
	side = blas.Side(upper(byte(side)))
	trans = blas.Transpose(upper(byte(trans)))
	if side != blas.Left && side != blas.Right {
		return ArgumentError("side")
	}
	if trans != blas.NoTrans && trans != blas.Trans && trans != blas.ConjTrans {
		return ArgumentError("trans")
	}
	m, n := a.Rows, a.Cols
	if m < 0 {
		return ArgumentError("rows")
	}
	if n < 0 {
		return ArgumentError("cols")
	}
	k := n
	if side == blas.Left {
		k = m
	}
	if h.Rows != k || h.Cols != k || h.Stride < max(1, k) {
		return ArgumentError("h")
	}
	if a.Stride < max(1, n) {
		return ArgumentError("a")
	}
	if b.Rows != m || b.Cols != n || b.Stride < max(1, n) {
		return ArgumentError("b")
	}
	if m == 0 || n == 0 {
		return nil
	}
	if !hasStorage(b) {
		return ArgumentError("b")
	}
	if alpha == 0 {
		for i := 0; i < m; i++ {
			clear(b.Data[i*b.Stride : i*b.Stride+n])
		}
		return nil
	}
	if !hasStorage(h) {
		return ArgumentError("h")
	}
	if !hasStorage(a) {
		return ArgumentError("a")
	}
	for i := 0; i < m; i++ {
		copy(b.Data[i*b.Stride:i*b.Stride+n], a.Data[i*a.Stride:i*a.Stride+n])
	}
	if trans == blas.ConjTrans {
		trans = blas.Trans
	}
	blas64.Trmm(side, trans, alpha, blas64.Triangular{N: k, Stride: h.Stride, Data: h.Data, Uplo: blas.Upper, Diag: blas.NonUnit}, b)
	for j := 0; j < k-1; j++ {
		v := h.Data[(j+1)*h.Stride+j]
		if side == blas.Left {
			dst, src := j+1, j
			if trans == blas.Trans {
				dst, src = j, j+1
			}
			for col := 0; col < n; col++ {
				b.Data[dst*b.Stride+col] += alpha * v * a.Data[src*a.Stride+col]
			}
		} else if v != 0 {
			dst, src := j, j+1
			if trans == blas.Trans {
				dst, src = j+1, j
			}
			blas64.Axpy(alpha*v, blas64.Vector{N: m, Inc: a.Stride, Data: a.Data[src:]}, blas64.Vector{N: m, Inc: b.Stride, Data: b.Data[dst:]})
		}
	}
	return nil
}

func upper(c byte) byte {
	if c >= 'a' && c <= 'z' {
		return c - ('a' - 'A')
	}
	return c
}

func hasStorage(a blas64.General) bool {
	if a.Rows == 0 || a.Cols == 0 {
		return true
	}
	return len(a.Data) >= a.Cols && (len(a.Data)-a.Cols)/a.Stride >= a.Rows-1
}
