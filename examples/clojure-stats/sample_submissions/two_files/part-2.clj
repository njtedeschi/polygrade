;;;; One of two files submitted together (only one is allowed).

(def sample-data '(2 4 4 4 5 5 7 9))

(defn square [x]
  (* x x))

(defn sum-of-squares [xs]
  (apply + (map square xs)))

(defn mean [xs]
  (/ (apply + xs) (count xs)))

(defn variance [xs]
  (let [m (mean xs)]
    (/ (apply + (map #(square (- % m)) xs))
       (count xs))))

(def sample-mean (mean sample-data))
