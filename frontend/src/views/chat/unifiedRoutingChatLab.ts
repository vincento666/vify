import type { RuntimeLabTask, RuntimeLabTurn } from '@/api/runtimeLab'

export interface AirlineSopScenario {
  id: string
  label: string
  shortLabel: string
  triggerUtterances: string[]
  sampleReplies: string[]
}

export interface RuntimeLabTranscriptRow {
  id: string
  role: 'user' | 'assistant'
  content: string
  routeAction?: string
  targetSopId?: string | null
  taskSummary?: string
  resumePrompt?: string
}

export const AIRLINE_SOP_SCENARIOS: AirlineSopScenario[] = [
  {
    id: 'flight_booking',
    label: '机票预订',
    shortLabel: '订票',
    triggerUtterances: [
      '我想买一张明天去上海的机票，时间最好别太早',
      '帮我订机票，两个人从北京飞成都，预算想控制一下',
      '临时出行需要订机票，麻烦帮我进入购票流程',
    ],
    sampleReplies: ['手机号 13800138000，乘机人张测试', '确认', '继续机票预订'],
  },
  {
    id: 'fare_quote',
    label: '票价咨询',
    shortLabel: '票价',
    triggerUtterances: [
      '我先不出票，想问下北京到上海今天票价大概多少',
      '帮我查一下机票报价，周五晚上飞深圳',
      '现在去成都的航班价格怎么样？我想比较一下',
    ],
    sampleReplies: ['订单号 CA0134，手机号 13800138000，乘机人张测试', '确认', '继续票价咨询'],
  },
  {
    id: 'group_booking',
    label: '团队订票',
    shortLabel: '团队',
    triggerUtterances: [
      '我们公司十六个人出差，想咨询团队机票怎么订',
      '帮我开团队订票流程，人数比较多需要统一出票',
      '团队机票能不能给报价？大概二十个人',
    ],
    sampleReplies: ['订单号 CA0234，手机号 13800138000，乘机人张测试', '确认', '继续团队订票'],
  },
  {
    id: 'ancillary_sales',
    label: '增值服务',
    shortLabel: '增值',
    triggerUtterances: [
      '买完票以后还能加购餐食和贵宾厅吗？',
      '我想给这张票加买保险和接送机服务',
      '帮我看看附加服务，行李和餐食一起买',
    ],
    sampleReplies: ['订单号 CA0334，手机号 13800138000，乘机人张测试', '确认', '继续增值服务'],
  },
  {
    id: 'refund_ticket',
    label: '退票办理',
    shortLabel: '退票',
    triggerUtterances: [
      '您好，我临时出差取消了，想把今晚这张机票退掉',
      '我不飞了，票款能不能退回来？',
      '昨天订错了航班，我要退票，但想先知道扣费',
    ],
    sampleReplies: ['订单号 CA1034，手机号 13800138000，乘机人张测试', '确认', '继续退票'],
  },
  {
    id: 'change_flight',
    label: '改签办理',
    shortLabel: '改签',
    triggerUtterances: [
      '我明天会议提前，想把航班改签到更早一班',
      '这趟来不及赶到机场，帮我换个航班',
      '计划变了，想调整航班时间，不知道差价多少',
    ],
    sampleReplies: ['订单号 CA2034，手机号 13800138000，乘机人张测试', '确认', '继续改签'],
  },
  {
    id: 'passenger_info_change',
    label: '资料修改',
    shortLabel: '资料',
    triggerUtterances: [
      '我证件号填错了一位，想修改乘机人信息',
      '订票时手机号写错了，能帮我改联系人吗？',
      '乘机人姓名拼音有问题，需要更正一下',
    ],
    sampleReplies: ['订单号 CA2134，手机号 13800138000，乘机人张测试', '确认', '继续资料修改'],
  },
  {
    id: 'invoice_apply',
    label: '发票申请',
    shortLabel: '发票',
    triggerUtterances: [
      '公司报销要凭证，帮我开一下电子发票',
      '我需要行程单和发票，抬头稍后给你',
      '上周飞完了，现在需要报销凭证',
    ],
    sampleReplies: ['订单号 CA3034，手机号 13800138000，乘机人张测试', '确认', '继续发票申请'],
  },
  {
    id: 'baggage_service',
    label: '行李服务',
    shortLabel: '行李',
    triggerUtterances: [
      '我带了两个箱子，想加购托运行李额',
      '行李可能超重，帮我看看能不能提前买',
      '我有婴儿车和箱子，问下行李怎么处理',
    ],
    sampleReplies: ['订单号 CA4034，手机号 13800138000，乘机人张测试', '确认', '继续行李服务'],
  },
  {
    id: 'seat_checkin',
    label: '值机选座',
    shortLabel: '选座',
    triggerUtterances: [
      '我想线上值机，最好选靠窗座位',
      '帮我选座，同行两个人想坐一起',
      '能不能帮我办登机牌？订单稍后发',
    ],
    sampleReplies: ['订单号 CA5034，手机号 13800138000，乘机人张测试', '确认', '继续值机选座'],
  },
  {
    id: 'flight_status',
    label: '航班动态',
    shortLabel: '动态',
    triggerUtterances: [
      '我想查一下今天航班动态，听说天气不好',
      '帮我看航班是不是延误了，机场通知不清楚',
      '查一下到达时间，司机在等',
    ],
    sampleReplies: ['订单号 CA6034，手机号 13800138000，乘机人张测试', '确认', '继续航班动态'],
  },
  {
    id: 'special_assistance',
    label: '特殊协助',
    shortLabel: '协助',
    triggerUtterances: [
      '老人第一次坐飞机，需要轮椅协助',
      '我腿受伤了，想申请特殊旅客服务',
      '我要申请特殊服务，航班信息稍后发',
    ],
    sampleReplies: ['订单号 CA2234，手机号 13800138000，乘机人张测试', '确认', '继续特殊协助'],
  },
  {
    id: 'pet_cabin',
    label: '宠物乘机',
    shortLabel: '宠物',
    triggerUtterances: [
      '我想带猫坐飞机，问下宠物进客舱要求',
      '我要办理宠物托运，小狗证件都有',
      '宠物能不能随身带？需要什么材料',
    ],
    sampleReplies: ['订单号 CA3234，手机号 13800138000，乘机人张测试', '确认', '继续宠物乘机'],
  },
  {
    id: 'irregular_flight',
    label: '异常航班',
    shortLabel: '异常',
    triggerUtterances: [
      '航班取消了，我需要改签或补偿方案',
      '延误四小时，客服说可以非自愿处理',
      '我遇到不正常航班，想知道能不能改到明天',
    ],
    sampleReplies: ['订单号 CA4234，手机号 13800138000，乘机人张测试', '确认', '继续异常航班'],
  },
  {
    id: 'membership_service',
    label: '会员里程',
    shortLabel: '会员',
    triggerUtterances: [
      '我的会员里程没到账，帮我补登一下',
      '常旅客账号积分不对，想查明细',
      '帮我补登里程，登机牌还在',
    ],
    sampleReplies: ['订单号 CA5234，手机号 13800138000，乘机人张测试', '确认', '继续会员里程'],
  },
]

export function getAirlineSopScenario(id: string) {
  return AIRLINE_SOP_SCENARIOS.find((scenario) => scenario.id === id) ?? null
}

export function buildUserTranscriptRow(id: string, content: string): RuntimeLabTranscriptRow {
  return {
    id,
    role: 'user',
    content,
  }
}

export function buildRuntimeLabTranscriptRow(turn: RuntimeLabTurn): RuntimeLabTranscriptRow {
  return {
    id: `assistant-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    role: 'assistant',
    content: turn.reply,
    routeAction: turn.routeDecision.action,
    targetSopId: turn.routeDecision.targetSopId,
    taskSummary: summarizeTasks(turn.activeTask, turn.suspendedTasks),
    resumePrompt: typeof turn.resumeOffer?.prompt === 'string' ? turn.resumeOffer.prompt : undefined,
  }
}

export function summarizeTasks(activeTask: RuntimeLabTask | null, suspendedTasks: RuntimeLabTask[]) {
  const chunks: string[] = []
  if (activeTask) chunks.push(`active: ${activeTask.sopId}`)
  if (suspendedTasks.length) chunks.push(`suspended: ${suspendedTasks.map((task) => task.sopId).join(', ')}`)
  return chunks.join(' | ') || 'no active task'
}
