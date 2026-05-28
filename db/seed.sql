-- Seed canonical topic vocabulary into roadmap_topics.
-- Run after 0001_init.sql, before the scraper populates starter/milestone problems.

INSERT INTO roadmap_topics (topic, ordinal, display_name, prerequisite_topics, summary, core_patterns)
VALUES
  ('arrays',            1,  'Arrays & Hashing',         '{}',                         'Linear collections, prefix sums, hashing for O(1) lookup.',         ARRAY['two-pointers','prefix-sum','hashing']),
  ('strings',           2,  'Strings',                  ARRAY['arrays'],              'String manipulation, sliding window on chars, anagram checks.',     ARRAY['sliding-window','two-pointers']),
  ('hashing',           3,  'Hash Maps & Sets',         ARRAY['arrays'],              'Frequency counts, grouping, existence queries in O(1).',            ARRAY['frequency-map','grouping']),
  ('two-pointers',      4,  'Two Pointers',             ARRAY['arrays','sorting'],    'Opposite-end and same-direction pointer techniques.',               ARRAY['opposite-ends','slow-fast']),
  ('sliding-window',    5,  'Sliding Window',           ARRAY['two-pointers'],        'Fixed and variable-size window on arrays/strings.',                 ARRAY['fixed-window','variable-window']),
  ('prefix-sum',        6,  'Prefix Sum',               ARRAY['arrays'],              'Range sum queries, subarray sum, 2D prefix.',                       ARRAY['prefix-sum','difference-array']),
  ('binary-search',     7,  'Binary Search',            ARRAY['arrays','sorting'],    'Search on sorted arrays, search on answer space.',                  ARRAY['classic-bs','search-on-answer']),
  ('linked-list',       8,  'Linked Lists',             ARRAY['arrays'],              'Singly/doubly linked lists, fast-slow pointer, reversal.',          ARRAY['fast-slow','reversal','dummy-node']),
  ('stacks-queues',     9,  'Stacks & Queues',          ARRAY['arrays'],              'Monotonic stack, queue, deque-based sliding window.',               ARRAY['monotonic-stack','deque']),
  ('recursion',         10, 'Recursion & Divide/Conquer', ARRAY['arrays'],            'Base case, recurrence, merge sort, D&C paradigm.',                  ARRAY['divide-conquer','tail-recursion']),
  ('backtracking',      11, 'Backtracking',             ARRAY['recursion'],           'Pruned exhaustive search: permutations, combinations, Sudoku.',     ARRAY['choose-explore-unchoose','pruning']),
  ('trees',             12, 'Binary Trees',             ARRAY['recursion'],           'DFS (pre/in/post), BFS (level order), path problems.',              ARRAY['tree-dfs','tree-bfs']),
  ('bst',               13, 'Binary Search Trees',      ARRAY['trees'],               'BST properties, insert/delete/search, inorder = sorted.',           ARRAY['bst-insert','bst-validate']),
  ('heap',              14, 'Heaps & Priority Queues',  ARRAY['trees'],               'Min/max heap, k-th element, top-K, merge K sorted.',               ARRAY['min-heap','top-k','k-way-merge']),
  ('greedy',            15, 'Greedy',                   ARRAY['arrays','sorting'],    'Locally optimal choice, interval scheduling, activity selection.',  ARRAY['interval-scheduling','exchange-argument']),
  ('dynamic-programming',16,'Dynamic Programming',      ARRAY['recursion','arrays'],  '1D/2D DP, memoization, tabulation, classical patterns.',            ARRAY['1d-dp','2d-dp','knapsack','lcs','lis']),
  ('graphs',            17, 'Graphs',                   ARRAY['trees','recursion'],   'BFS/DFS on graphs, topological sort, Dijkstra, Union-Find.',        ARRAY['bfs','dfs','topo-sort','dijkstra','union-find']),
  ('tries',             18, 'Tries',                    ARRAY['trees','hashing'],     'Prefix tree, word search, auto-complete.',                          ARRAY['trie-insert','trie-search']),
  ('segment-trees',     19, 'Segment Trees & BIT',      ARRAY['trees','prefix-sum'],  'Range queries with updates: segment tree, Fenwick tree.',           ARRAY['segment-tree','fenwick-tree']),
  ('bit-manipulation',  20, 'Bit Manipulation',         ARRAY['math'],                'XOR tricks, bit masking, power-of-two checks.',                     ARRAY['xor-tricks','bit-mask']),
  ('math',              21, 'Math & Number Theory',     '{}',                         'GCD, primes, modular arithmetic, combinatorics.',                   ARRAY['gcd','sieve','modular-exp']),
  ('string-algorithms', 22, 'String Algorithms',        ARRAY['strings','hashing'],   'KMP, Rabin-Karp, Z-function, string hashing.',                     ARRAY['kmp','rabin-karp','z-function'])
ON CONFLICT (topic) DO NOTHING;
