# 034.6 Badcases And Fixes

- `机票销售流程...订一张` did not start `flight_booking`.
  Added `机票销售` and more specific booking templates.
- `加购托运行李额` was captured by ancillary sales.
  Removed broad standalone `加购` from strong ancillary triggers.
- `不出票/不用买票` was treated as a user refusal.
  Added embedded-business-negation handling so price-consult turns keep routing.
- `非自愿退票` was captured by irregular flight.
  Added a higher-priority `非自愿 + 退票` refund template.
- Group booking utterances containing `出票`, `报价`, `购票`, or `订航班`
  were captured by ordinary booking or fare quote.
  Raised group-booking template scores and narrowed ordinary booking templates.
- Passenger information changes containing `航班` were captured by flight
  change.
  Narrowed change-flight regexes and added stronger passenger-info templates.
- Flight status questions containing `延误/取消` were captured by irregular
  flight.
  Removed broad irregular `航班 + 延误/取消` templates and kept only stronger
  abnormal-flight phrases.
- Membership turns mentioning `登机牌` or `升舱券` were captured by seat check-in
  or ancillary sales.
  Raised membership core-template scores when `会员/里程/积分/常旅客` is present.

Final result: 150 backend realistic start cases, five switch/resume journeys,
and 15 browser UAT journeys pass.
