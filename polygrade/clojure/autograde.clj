;;;; Runs an assignment's unit tests against a submission.
;;;;
;;;; Usage (any command that runs a Clojure script works in place of lein exec):
;;;;   lein exec autograde.clj grading.clj unit-tests.clj solution.clj submission.clj
;;;;
;;;; The solution and the submission are loaded into the namespaces `solution`
;;;; and `student`, so tests can call both versions of a function side by side.
;;;; The unit tests file must declare the namespace `unit-tests`.

(ns autograde
  (:require [clojure.string :as str]
            [clojure.test :as test]))

(defn load-into-namespace
  "Load `file` into a fresh namespace named `ns-sym`."
  [file ns-sym]
  (binding [*ns* (create-ns ns-sym)]
    (refer 'clojure.core)
    (load-file file)))

(defn stub-missing-definitions
  "Intern an unbound var in `student` for everything the solution defines but
  the submission doesn't. Tests that use a missing definition then fail with a
  runtime error, instead of the whole test file failing to compile."
  []
  (doseq [sym (keys (ns-publics 'solution))
          :when (not (contains? (ns-interns 'student) sym))]
    (intern 'student sym)))

(defn -main [grading-library unit-tests solution submission]
  (println "Loading files")
  (load-file grading-library)
  (load-into-namespace solution 'solution)
  (load-into-namespace submission 'student)
  (stub-missing-definitions)
  (load-file unit-tests)
  (println "Running tests")
  (test/run-tests 'unit-tests))

;; `lein exec` passes the script's own path as the first argument; `clojure.main` doesn't.
(let [args (cond->> *command-line-args*
             (some-> (first *command-line-args*) (str/ends-with? "autograde.clj")) rest)]
  (apply -main args)
  (shutdown-agents))
