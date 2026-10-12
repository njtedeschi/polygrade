;;;; Macros and helpers for writing autograder unit tests.
;;;;
;;;; A unit tests file starts with:
;;;;
;;;;   (ns unit-tests
;;;;     (:require [clojure.test :refer :all]))
;;;;   (refer 'polygrade.grading)
;;;;
;;;; Failure messages are how results get back to Gradescope: a message starting
;;;; with "Q<n>: " fails problem n, and one starting with "PC<tag>: " flags a
;;;; known mistake for partial credit. The macros below add these prefixes.

(ns polygrade.grading
  (:require [clojure.test :refer [deftest is]]))

(def debug?
  "When the POLYGRADE_DEBUG environment variable is set, tests print the
  student's and the solution's output for every test input."
  (some? (System/getenv "POLYGRADE_DEBUG")))

(defn qualified
  "The symbol for `fn-name` in the `student` or `solution` namespace."
  [ns-name fn-name]
  (symbol (str ns-name) (str fn-name)))

(defn mock-bindings
  "`with-redefs` bindings replacing the student's version of each function with the solution's."
  [fns-to-mock]
  (mapcat (fn [fn-name] [(qualified 'student fn-name) (qualified 'solution fn-name)])
          fns-to-mock))

;;;; Comparing the student's output with the solution's

(defmacro unit-test
  "Define a test that `comparison-fn` holds of the student's and the solution's
  output for `args`, with the functions named in `fns-to-mock` replaced by the
  solution's versions (so mistakes in them aren't penalized twice)."
  [test-name comparison-fn fn-name args fail-message fns-to-mock]
  (let [student-fn (qualified 'student fn-name)
        solution-fn (qualified 'solution fn-name)]
    `(deftest ~(symbol test-name)
       (with-redefs [~@(mock-bindings fns-to-mock)]
         (when debug?
           (println ~test-name
                    "Student:" (try (~student-fn ~@args) (catch Exception e# "ERROR"))
                    "Solution:" (~solution-fn ~@args)))
         (is (~comparison-fn (~student-fn ~@args) (~solution-fn ~@args))
             ~fail-message)))))

(defmacro Q-tests
  "Define one `unit-test` for problem `problem-num` per entry of `test-cases`,
  each a vector [comparison-fn args fail-message]."
  [problem-num fn-name fns-to-mock test-cases]
  `(do ~@(map-indexed (fn [i [comparison-fn args fail-message]]
                        `(unit-test ~(str "Q" problem-num "-test-" i)
                                    ~comparison-fn
                                    ~fn-name
                                    ~args
                                    ~(str "Q" problem-num ": " fail-message)
                                    ~fns-to-mock))
                      test-cases)))

;;;; Detecting known mistakes for partial credit

(defmacro PC-test
  "Define a test that flags the mistake `tag` (e.g. \"3.1\") when the student's
  output for `args` matches `incorrect-result`, the output a submission with
  that mistake produces, according to `matches-fn`. The config maps the tag to
  an amount of partial credit for the corresponding problem."
  [tag matches-fn fn-name incorrect-result args fail-message fns-to-mock]
  (let [student-fn (qualified 'student fn-name)
        test-name (str "PC" (.replace (str tag) "." "_") "-test")]
    `(deftest ~(symbol test-name)
       (with-redefs [~@(mock-bindings fns-to-mock)]
         (is (not (~matches-fn (~student-fn ~@args) ~incorrect-result))
             ~(str "PC" tag ": " fail-message))))))

;;;; Comparison functions

(defn almost-eq?
  "Numbers within `epsilon` of each other. A student's -Infinity also matches
  NaN in the solution (e.g. the log of a zero probability computed two ways)."
  [epsilon]
  (fn [x y]
    (or (== x y)
        (and (= x Double/NEGATIVE_INFINITY) (Double/isNaN y))
        (<= (Math/abs (double (- x y))) epsilon))))

(defn not-almost-eq?
  [epsilon]
  (complement (almost-eq? epsilon)))

(defn lists-almost-eq?
  "Sequences of numbers of the same length that are element-wise `almost-eq?`."
  [epsilon]
  (fn [xs ys]
    (and (= (count xs) (count ys))
         (every? true? (map (almost-eq? epsilon) xs ys)))))

(defn matches-solution?
  "Whether the student's and solution's `fn-name` agree on `args` according to
  `comparison-fn`. Useful in hand-written tests, e.g. to check that a function
  doesn't depend on helpers it shouldn't by mocking them with wrong versions:

    (deftest Q7-test-independent-of-helper
      (with-redefs [student/helper (constantly 0)]
        (is (matches-solution? (almost-eq? 1e-6) \"f\" [1 2])
            \"Q7: f gives different results when helper is wrong\")))"
  [comparison-fn fn-name args]
  (let [student-fn (ns-resolve 'student (symbol fn-name))
        solution-fn (ns-resolve 'solution (symbol fn-name))]
    (comparison-fn (apply student-fn args) (apply solution-fn args))))
