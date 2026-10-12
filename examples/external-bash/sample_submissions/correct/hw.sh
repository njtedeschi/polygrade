# A fully correct submission.

greet() {
    printf 'Hello, %s!\n' "$1"
}

word_count() {
    echo "$#"
}
