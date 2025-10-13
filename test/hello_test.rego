package hello

test_allow_hello_allowed if{
  allow_hello with input as {}
}

test_allow_world_not_allowed if {
  not allow_world with input as {}
}