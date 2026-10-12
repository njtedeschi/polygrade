# A submission with a mistake in each problem.

greet() {
    echo "Hello $1"   # missing the comma and exclamation mark
}

word_count() {
    local all="$*"
    echo "${#all}"   # counts characters: flagged by PC2.1 for partial credit
}
