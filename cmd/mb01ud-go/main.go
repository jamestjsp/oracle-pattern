package main

import (
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"strconv"

	"github.com/jamestjsp/oracle-pattern/hessenberg"
	"gonum.org/v1/gonum/blas"
	"gonum.org/v1/gonum/blas/blas64"
)

const guard = -987654321.125

type input struct {
	ID      string   `json:"id"`
	Side    string   `json:"side"`
	Trans   string   `json:"trans"`
	M       int      `json:"m"`
	N       int      `json:"n"`
	Alpha   string   `json:"alpha"`
	Pad     int      `json:"pad"`
	Invalid int      `json:"invalid"`
	H       []string `json:"h"`
	A       []string `json:"a"`
	B       []string `json:"b"`
}

type output struct {
	Info      int      `json:"info"`
	PaddingOK bool     `json:"padding_ok"`
	H         []string `json:"h"`
	A         []string `json:"a"`
	B         []string `json:"b"`
}

func main() {
	if err := run(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(2)
	}
}

func run() error {
	var c input
	d := json.NewDecoder(os.Stdin)
	d.DisallowUnknownFields()
	if err := d.Decode(&c); err != nil {
		return err
	}
	if len(c.Side) != 1 || len(c.Trans) != 1 || c.M < 0 || c.N < 0 || c.Pad < 0 || c.M > 256 || c.N > 256 || c.Pad > 256 {
		return errors.New("invalid wire dimensions or flags")
	}
	k := c.N
	if c.Side == "L" || c.Side == "l" {
		k = c.M
	}
	h, err := pack(k, k, c.Pad, c.H)
	if err != nil {
		return err
	}
	a, err := pack(c.M, c.N, c.Pad, c.A)
	if err != nil {
		return err
	}
	b, err := pack(c.M, c.N, c.Pad, c.B)
	if err != nil {
		return err
	}
	alpha, err := strconv.ParseFloat(c.Alpha, 64)
	if err != nil {
		return err
	}
	hc, ac, bc := h, a, b
	side, trans := blas.Side(c.Side[0]), blas.Transpose(c.Trans[0])
	switch c.Invalid {
	case 0:
	case 1:
		side = '?'
	case 2:
		trans = '?'
	case 3:
		ac.Rows = -1
	case 4:
		ac.Cols = -1
	case 7:
		hc.Stride = 0
	case 9:
		ac.Stride = 0
	case 11:
		bc.Stride = 0
	default:
		return errors.New("unsupported invalid argument probe")
	}
	err = hessenberg.Product(side, trans, alpha, hc, ac, bc)
	info := 0
	if err != nil {
		var arg hessenberg.ArgumentError
		if !errors.As(err, &arg) {
			return err
		}
		var ok bool
		info, ok = map[hessenberg.ArgumentError]int{"side": -1, "trans": -2, "rows": -3, "cols": -4, "h": -7, "a": -9, "b": -11}[arg]
		if !ok {
			return err
		}
	}
	return json.NewEncoder(os.Stdout).Encode(output{info, padding(h) && padding(a) && padding(b), unpack(h), unpack(a), unpack(b)})
}

func pack(rows, cols, pad int, values []string) (blas64.General, error) {
	a := blas64.General{Rows: rows, Cols: cols, Stride: max(1, cols) + pad}
	if len(values) != rows*cols {
		return a, errors.New("wire matrix length mismatch")
	}
	a.Data = make([]float64, max(1, rows)*a.Stride)
	for i := range a.Data {
		a.Data[i] = guard
	}
	for i := 0; i < rows; i++ {
		for j := 0; j < cols; j++ {
			v, err := strconv.ParseFloat(values[i*cols+j], 64)
			if err != nil {
				return a, err
			}
			a.Data[i*a.Stride+j] = v
		}
	}
	return a, nil
}

func unpack(a blas64.General) []string {
	values := make([]string, 0, a.Rows*a.Cols)
	for i := 0; i < a.Rows; i++ {
		for j := 0; j < a.Cols; j++ {
			values = append(values, strconv.FormatFloat(a.Data[i*a.Stride+j], 'g', -1, 64))
		}
	}
	return values
}

func padding(a blas64.General) bool {
	for i, v := range a.Data {
		if (i/a.Stride >= a.Rows || i%a.Stride >= a.Cols) && v != guard {
			return false
		}
	}
	return true
}
