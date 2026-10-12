;;;; A submission with a mix of mistakes, to show how each is graded.

(def sample-data '(2 4 4 4 5 5 7 9))

(defn square
  "Docstrings are fine."
  [x]
  (* x x))

(defn sum-of-squares [xs]
  (apply + (map square xs)))

;; Mistake: forgot to divide. Flagged by PC3.1 for partial credit.
(defn mean [xs]
  (apply + xs))

;; Same mistake again. Flagged by PC4.1, but waived because of PC3.1.
(defn variance [xs]
  (let [m (mean xs)]
    (apply + (map #(square (- % m)) xs))))

;; Wrong because mean is wrong; variables can't be graded with mocks.
(def sample-mean (mean sample-data))

;; Defined twice: reported by the (zero-point) duplicates check.
(defn square [x] (* x x))
