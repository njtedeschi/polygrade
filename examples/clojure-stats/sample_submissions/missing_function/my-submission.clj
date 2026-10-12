;;;; A submission missing variance. Only the problem using it loses points.

(def sample-data '(2 4 4 4 5 5 7 9))

(defn square [x]
  (* x x))

(defn sum-of-squares [xs]
  (reduce + 0 (map square xs)))

(defn mean [xs]
  (/ (reduce + xs) (count xs)))

(def sample-mean (mean sample-data))
