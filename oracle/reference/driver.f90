program mb01ud_oracle
  implicit none
  character :: side, trans
  integer :: m, n, k, pad, bad, mm, nn, lh, la, lb, info, i, j, stat, handler
  real(8) :: alpha
  real(8), allocatable :: h(:,:), a(:,:), b(:,:)
  real(8), parameter :: guard = -987654321.125d0
  logical :: padding_ok
  common /error_observation/ handler

  read(*,*,iostat=stat) side, trans, m, n, alpha, pad, bad
  if (stat /= 0 .or. m < 0 .or. n < 0 .or. pad < 0) stop 2
  k = n
  if (side == 'L' .or. side == 'l') k = m
  lh = max(1,k) + pad
  la = max(1,m) + pad
  lb = la
  allocate(h(lh,max(1,k)), a(la,max(1,n)), b(lb,max(1,n)))
  h = guard
  a = guard
  b = guard
  do i = 1,k
    read(*,*) (h(i,j), j=1,k)
  end do
  do i = 1,m
    if (n > 0) read(*,*) (a(i,j), j=1,n)
  end do
  do i = 1,m
    if (n > 0) read(*,*) (b(i,j), j=1,n)
  end do
  mm = m
  nn = n
  select case (bad)
  case (1)
    side = '?'
  case (2)
    trans = '?'
  case (3)
    mm = -1
  case (4)
    nn = -1
  case (7)
    lh = 0
  case (9)
    la = 0
  case (11)
    lb = 0
  end select
  handler = 0
  call MB01UD(side, trans, mm, nn, alpha, h, lh, a, la, b, lb, info)
  padding_ok = all(h(k+1:,:) == guard) .and. all(a(m+1:,:) == guard) .and. all(b(m+1:,:) == guard)
  if (k == 0) padding_ok = padding_ok .and. all(h == guard)
  if (n == 0) padding_ok = padding_ok .and. all(a == guard) .and. all(b == guard)
  write(*,*) info, handler, merge(1,0,padding_ok)
  do i = 1,k
    write(*,'(*(ES26.17E3,1X))') (h(i,j), j=1,k)
  end do
  do i = 1,m
    if (n > 0) write(*,'(*(ES26.17E3,1X))') (a(i,j), j=1,n)
  end do
  do i = 1,m
    if (n > 0) write(*,'(*(ES26.17E3,1X))') (b(i,j), j=1,n)
  end do
end program

subroutine xerbla(name, argument)
  implicit none
  character(*) :: name
  integer :: argument, handler
  common /error_observation/ handler
  if (name /= 'MB01UD') stop 3
  handler = argument
end subroutine
