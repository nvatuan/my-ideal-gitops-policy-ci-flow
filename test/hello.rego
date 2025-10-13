package hello

default allow_hello = false

default allow_world = false

allow_hello if {
  "hello" != ""
}

allow_world if {
  "world" != "world"
}