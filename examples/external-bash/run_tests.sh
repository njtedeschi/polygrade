#!/usr/bin/env bash
# Unit tests for the example Bash assignment.
# Usage: run_tests.sh SOLUTION SUBMISSION

solution=$1
submission=$2

# Call function $2 of script $1 with the remaining arguments, in a fresh shell
call() {
    local script=$1
    shift
    bash -c 'source "$0" >/dev/null 2>&1 && "$@"' "$script" "$@" 2>/dev/null
}

# check PROBLEM MESSAGE FUNCTION ARGS...: compare the submission with the solution
check() {
    local problem=$1 message=$2 expected actual
    shift 2
    expected=$(call "$solution" "$@")
    if ! actual=$(call "$submission" "$@"); then
        echo "ERROR Q$problem: $message"
    elif [[ "$actual" != "$expected" ]]; then
        echo "FAIL Q$problem: $message"
    fi
}

# flag TAG MESSAGE INCORRECT_OUTPUT FUNCTION ARGS...: detect a known mistake
flag() {
    local tag=$1 message=$2 incorrect=$3
    shift 3
    if [[ "$(call "$submission" "$@")" == "$incorrect" ]]; then
        echo "FAIL PC$tag: $message"
    fi
}

# Problem 1: greet NAME
check 1 "incorrect greeting" greet Ada
check 1 "incorrect greeting for a name with a space" greet "Grace Hopper"

# Problem 2: word_count WORDS...
check 2 "incorrect count for four words" word_count the quick brown fox
check 2 "incorrect count for no words" word_count
flag 2.1 "counted characters" 3 word_count abc

exit 0
