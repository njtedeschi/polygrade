;;;; Unit tests for the example Clojure assignment.
;;;;
;;;; Every failure message must start with "Q<problem number>: " (or "PC<tag>: "
;;;; for partial credit detectors); Q-tests and PC-test add these prefixes.

(ns unit-tests
  (:require [clojure.test :refer :all]))
(refer 'polygrade.grading)

;;;; Test inputs
(def data '(2 4 4 4 5 5 7 9))
(def data-2 '(-1.5 0 1.5 3))

;; Problem 1: (square x)
(Q-tests 1
         "square"
         []
         [[= [3] "incorrect result for a positive integer"]
          [(almost-eq? 1e-9) [-1.5] "incorrect result for a negative decimal"]])

;; Problem 2: (sum-of-squares xs), graded with the solution's square
(Q-tests 2
         "sum-of-squares"
         ["square"]
         [[(almost-eq? 1e-9) [data] "incorrect results for test inputs"]
          [(almost-eq? 1e-9) ['()] "incorrect result for an empty list"]])

;; A hand-written test: sum-of-squares shouldn't depend on mean
(deftest Q2-test-independent-of-mean
  (with-redefs [student/mean (constantly 0)]
    (is (matches-solution? (almost-eq? 1e-9) "sum-of-squares" [data])
        "Q2: sum-of-squares should not use mean")))

;; Problem 3: (mean xs)
(Q-tests 3
         "mean"
         []
         [[(almost-eq? 1e-9) [data] "incorrect results for test inputs"]
          [(almost-eq? 1e-9) [data-2] "incorrect results for test inputs"]])

;; Flags submissions that return the sum instead of the mean (40 for `data`)
(PC-test "3.1"
         (almost-eq? 1e-9)
         "mean"
         40
         [data]
         "returned the sum of the list instead of its mean"
         [])

;; Problem 4: (variance xs), graded with the solution's mean and square
(Q-tests 4
         "variance"
         ["mean" "square"]
         [[(almost-eq? 1e-9) [data] "incorrect results for test inputs"]
          [(almost-eq? 1e-9) [data-2] "incorrect results for test inputs"]])

(PC-test "4.1"
         (almost-eq? 1e-9)
         "variance"
         32
         [data]
         "returned the sum of squared deviations without dividing by the number of elements"
         ["mean" "square"])

;; Problem 5: sample-mean (a variable rather than a function)
(deftest Q5-test
  (is ((almost-eq? 1e-9) student/sample-mean solution/sample-mean)
      "Q5: incorrect value"))
