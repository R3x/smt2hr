(set-logic QF_AUFBV )
(declare-fun foo_arg_0_dynSize () (Array (_ BitVec 32) (_ BitVec 8) ) )
(declare-fun foo_arg_1 () (Array (_ BitVec 32) (_ BitVec 8) ) )
(declare-fun foo_arg_2 () (Array (_ BitVec 32) (_ BitVec 8) ) )
(assert (let ( (?B1 (concat (select foo_arg_1 (_ bv3 32) ) (concat (select foo_arg_1 (_ bv2 32) ) (concat (select foo_arg_1 (_ bv1 32) ) (select foo_arg_1 (_ bv0 32) ) ) ) ) ) ) (and (and (= (_ bv5 32) (bvurem (concat (select foo_arg_0_dynSize (_ bv3 32) ) (concat (select foo_arg_0_dynSize (_ bv2 32) ) (concat (select foo_arg_0_dynSize (_ bv1 32) ) (select foo_arg_0_dynSize (_ bv0 32) ) ) ) ) (_ bv129 32) ) ) (bvslt ?B1 (concat (select foo_arg_2 (_ bv3 32) ) (concat (select foo_arg_2 (_ bv2 32) ) (concat (select foo_arg_2 (_ bv1 32) ) (select foo_arg_2 (_ bv0 32) ) ) ) ) ) ) (= (_ bv131068 32) ((_ extract 31 0) (bvmul (_ bv4 64) ((_ sign_extend 32) ?B1 ) ) ) ) ) ) )
(check-sat)
(exit)